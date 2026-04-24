from datetime import datetime, timedelta
import traceback
from PySide6.QtCore import Signal, Qt, QThread, QTimer
from PySide6.QtWidgets import QWidget, QSizePolicy

from data.utils.status_manager import StatusMsg
from data.repositories.book_repo import BookRepository
from data.repositories.statistics_repo import StatsRepository
from data.repositories.activity_repo import ActivityRepository
from charts.activity_charts import ActivityChart, ActivityHeatmap
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips
from worker import DatabaseWorker

class ChartRenderWorker(QThread):
    """Renderuje wykresy matplotlib w tle (nie blokuje UI)"""
    finished = Signal()

    def __init__(self, canvas, heatmap, chart_data):
        super().__init__()
        self.canvas = canvas
        self.heatmap = heatmap
        self.chart_data = chart_data

    def run(self):
        """Renderuje wykresy w osobnym wątku"""
        try:
            dates, values = self.chart_data
            # Plot w tle
            self.canvas.plot_data(list(dates), list(values), time_filter="month")

            # Heatmap w tle
            if hasattr(self, 'heatmap_data'):
                self.heatmap.plot_heatmap(self.heatmap_data)
        finally:
            self.finished.emit()

class DashboardView(QWidget):
    """Główny panel z dynamicznym skalowaniem i optymalnym wykorzystaniem przestrzeni."""
    statusMessage = Signal(str, str)
    renderingFinished = Signal()  # Wyemituje się kiedy wykresy się wyrenderują

    def __init__(self, conn):
        super().__init__()
        from datetime import datetime as dt
        t_init = dt.now()
        print(f"[DASHBOARD_INIT] START at {t_init.strftime('%H:%M:%S.%f')[:-3]}")

        self.conn = conn

        # Ładowanie zaktualizowanego UI
        self.ui = load_ui(self, "views/ui/DashboardView.ui")
        if not self.ui: return

        self.stats_repo = StatsRepository(conn)
        self.book_repo = BookRepository(conn)
        self.activity_repo = ActivityRepository(conn)

        # Nie inicjalizuje matplotlib od razu
        self.canvas = None
        self.heatmap = None

        # Obsługa zdarzeń
        self.ui.btn_refresh.clicked.connect(self.load_view)

        self._current_worker = None

        # Setup charts asynchronicznie na Qt event loop (po pokazaniu UI)
        QTimer.singleShot(0, self._setup_charts_deferred)

        print(f"[DASHBOARD_INIT] DONE at {dt.now().strftime('%H:%M:%S.%f')[:-3]} ({(dt.now()-t_init).total_seconds()*1000:.0f}ms)")

    def setup_charts(self):
        """Inicjalizacja wykresów z wymuszeniem elastyczności rozmiaru."""
        # Wykres Trendu
        self.canvas = ActivityChart(self.ui.frame_chart)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self.ui, 'lbl_activity_chart'):
            self.ui.verticalLayout_3.replaceWidget(self.ui.lbl_activity_chart, self.canvas)
            self.ui.lbl_activity_chart.deleteLater()

        # Heatmapa (30 kafli)
        self.heatmap = ActivityHeatmap(self.ui.heatmap_container)
        self.heatmap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self.ui, 'lbl_heatmap_placeholder'):
            self.ui.verticalLayout_heatmap.replaceWidget(self.ui.lbl_heatmap_placeholder, self.heatmap)
            self.ui.lbl_heatmap_placeholder.deleteLater()

    def _setup_charts_deferred(self):
        """Setup charts w tle po pokazaniu UI (nie blokuje startup)."""
        from datetime import datetime as dt
        print(f"[DASHBOARD_CHARTS] SETUP START at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")
        self.setup_charts()
        self.setup_tooltips()
        print(f"[DASHBOARD_CHARTS] SETUP DONE at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

    def load_view(self):
        """Załaduje dane Dashboard'a w tle (worker thread)."""
        # Safety check - jeśli charts nie istnieją, trigger setup
        if self.canvas is None or self.heatmap is None:
            print("[WARNING] Charts missing on load_view(), re-initializing...")
            self.setup_charts()

        # Force redraw na canvasach (w przypadku gdy widget był ukryty, może nie renderować poprawnie)
        if self.canvas:
            self.canvas.draw()
        if self.heatmap:
            self.heatmap.draw()

        # Pokazuje loading state
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Dashboard"))
        self._set_loading_state(True)
        from datetime import datetime as dt
        print(f"[TIMING] Dashboard.load_view() started at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

        # Jeśli dane są już preloaded (z MainWindow) - używa ich od razu
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, '_preloaded_dashboard_data'):
            parent_window = parent_window.parent()

        if parent_window and hasattr(parent_window, '_preloaded_dashboard_data') and parent_window._preloaded_dashboard_data:
            # Używa preloaded data
            print(f"[TIMING] Using preloaded dashboard data")
            self._on_dashboard_data_loaded(parent_window._preloaded_dashboard_data)
        else:
            # Fallback - uruchamia worker w tle
            self._current_worker = DatabaseWorker("load_dashboard", db_connection=self.conn)
            self._current_worker.finished.connect(self._on_dashboard_data_loaded)
            self._current_worker.error.connect(self._on_dashboard_error)
            self._current_worker.start()

    def _on_dashboard_data_loaded(self, data):
        """Callback gdy worker załaduje dane."""
        from datetime import datetime as dt
        print(f"[TIMING] Dashboard data received at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")
        try:
            if data:
                self._update_dashboard_ui(data)
                self.statusMessage.emit(*StatusMsg.get("ACTIVITY_UPDATED", "Dashboard", "Global"))
            self._set_loading_state(False)
        except Exception as e:
            traceback.print_exc()
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))
            self._set_loading_state(False)

    def _on_dashboard_error(self, error_msg):
        """Callback gdy worker napotka błąd."""
        self.statusMessage.emit(*StatusMsg.get("DB_ERROR", error_msg))
        self._set_loading_state(False)

    def _update_dashboard_ui(self, data):
        """Aktualizuje UI z załadowanymi danymi."""
        total_users = data.get("total_users", 0)
        new_users = data.get("new_users", 0)
        avg_pages = data.get("avg_pages", 0)
        books_month = data.get("books_month", 0)
        top_3_streaks = data.get("top_3_streaks", [])
        activity_data = data.get("activity_data", [])

        # Formatowanie tekstu
        accent = "#daa520"
        style = f"color:{accent}; font-weight:bold; font-size:16pt;"
        self.ui.lbl_users.setText(f"Users: <br><span style='{style}'>{total_users}</span>")
        self.ui.lbl_books.setText(f"Books read: <br><span style='{style}'>{books_month or 0}</span>")
        self.ui.lbl_pages.setText(f"Pages / day: <br><span style='{style}'>{round(avg_pages, 1)}</span>")

        # Top 3 streaks
        streak_text = "<span style='font-size:11pt;'><b>Top Streaks:</b><br>"
        for i, (username, streak) in enumerate(top_3_streaks, 1):
            streak_text += f"{i}. {username} ({streak}d)<br>"
        streak_text += "</span>"
        self.ui.lbl_streak.setText(streak_text)

        # Aktualizacja wykresów - opóźnia rendering
        processed_data = self._prepare_30_days(activity_data)
        if processed_data:
            dates, values = zip(*processed_data) if processed_data else ([], [])
            chart_data = (list(dates), list(values))

            # Zaplanuje rendering na później (500ms) - uruchamia placeholder
            def start_chart_render():
                self._chart_worker = ChartRenderWorker(self.canvas, self.heatmap, chart_data)
                self._chart_worker.heatmap_data = processed_data
                self._chart_worker.finished.connect(self._on_charts_rendered)
                self._chart_worker.start()

            QTimer.singleShot(500, start_chart_render)

        from datetime import datetime as dt
        print(f"[TIMING] Dashboard UI fully rendered at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

    def _on_charts_rendered(self):
        """Callback kiedy wykresy się wyrenderują w tle"""
        from datetime import datetime as dt
        print(f"[DASHBOARD_READY] Charts fully rendered at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")
        self.renderingFinished.emit()

    def _set_loading_state(self, is_loading):
        """Pokazuje/ukrywa loading state z placeholderem."""
        if is_loading:
            # Loading placeholders dla metryk
            loading_style = "color: #999; font-style: italic;"
            self.ui.lbl_users.setText(f"<span style='{loading_style}'>[LOADING...]</span>")
            self.ui.lbl_books.setText(f"<span style='{loading_style}'>[LOADING...]</span>")
            self.ui.lbl_pages.setText(f"<span style='{loading_style}'>[LOADING...]</span>")
            self.ui.lbl_streak.setText(f"<span style='{loading_style}'>[LOADING...]</span>")

            # Placeholder dla wykresów (tylko jeśli canvas już się zainicjalizował)
            if self.canvas and self.canvas.axes:
                self.canvas.axes.clear()
                self.canvas.axes.text(0.5, 0.5, '[LOADING CHART DATA...]',
                                  ha='center', va='center',
                                  fontsize=12, color='#999', style='italic',
                                  transform=self.canvas.axes.transAxes)
                self.canvas.draw()

            if self.heatmap and self.heatmap.axes:
                self.heatmap.axes.clear()
                self.heatmap.axes.text(0.5, 0.5, '[LOADING HEATMAP...]',
                                   ha='center', va='center',
                                   fontsize=12, color='#999', style='italic',
                                   transform=self.heatmap.axes.transAxes)
                self.heatmap.draw()
        else:
            # Loading state ukryty - UI będzie aktualizowany przez _update_dashboard_ui()
            pass

    def _prepare_30_days(self, data):
        """Generuje listę 30 ostatnich dni."""
        end_date = datetime.now().date()

        date_map = {}
        if data:
            for d, v in data:
                d_key = d if isinstance(d, str) else d.strftime("%Y-%m-%d")
                date_map[d_key] = v

        full_period = []
        for i in range(29, -1, -1):
            day = end_date - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            full_period.append((day_str, date_map.get(day_str, 0)))

        return full_period

    def setup_tooltips(self):
        """Definiowanie kontekstowych podpowiedzi dla elementów interfejsu."""
        tooltips = {
            "lbl_users": "Total registered users and growth (+X) within the last 30 days.",
            "lbl_books": "Number of books finished this month across the whole community.",
            "lbl_pages": "Average pages read daily per active user.",
            "lbl_streak": "Top 3 users with the longest reading streaks.",
            "btn_refresh": "Click to recalculate all community statistics."
        }
        apply_tooltips(self.ui, tooltips)