from datetime import datetime, timedelta
import traceback
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QSizePolicy

from data.utils.status_manager import StatusMsg
from data.repositories.book_repo import BookRepository
from data.repositories.statistics_repo import StatsRepository
from data.repositories.activity_repo import ActivityRepository
from charts.activity_charts import ActivityChart, ActivityHeatmap
from data.utils.ui_helpers import load_ui, apply_tooltips

class DashboardView(QWidget):
    """Główny panel z dynamicznym skalowaniem i optymalnym wykorzystaniem przestrzeni."""
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie zaktualizowanego UI
        self.ui = load_ui(self, "views/ui/DashboardView.ui")
        if not self.ui: return

        self.stats_repo = StatsRepository(conn)
        self.book_repo = BookRepository(conn)
        self.activity_repo = ActivityRepository(conn)

        # Konfiguracja komponentów graficznych
        self.setup_charts()
        self.setup_tooltips()
        
        # Obsługa zdarzeń
        self.ui.btn_refresh.clicked.connect(self.load_view)
        
        # Pierwsze wypełnienie danych
        self.load_view()

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

    def load_view(self):
        """Pobieranie danych i aktualizacja widoku w jednym cyklu."""
        try:
            self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Dashboard"))

            # Pobieranie metryk KPI
            metrics = self.stats_repo.get_dashboard_metrics()
            total_users, new_users, avg_pages = metrics if metrics else (0, 0, 0)
            books_month = self.book_repo.count_books_read(period="month")

            # Formatowanie tekstu
            accent = "#daa520"
            style = f"color:{accent}; font-weight:bold; font-size:16pt;"
            self.ui.lbl_users.setText(f"Users: <br><span style='{style}'>{total_users}</span>")
            self.ui.lbl_books.setText(f"Books read: <br><span style='{style}'>{books_month or 0}</span>")
            self.ui.lbl_pages.setText(f"Pages / day: <br><span style='{style}'>{round(avg_pages, 1)}</span>")

            # Pobieranie 30 dni danych
            data_raw = self.activity_repo.get_activity_trend("month")
            processed_data = self._prepare_30_days(data_raw)
            
            # Aktualizacja wykresów
            dates, values = zip(*processed_data)
            self.canvas.plot_data(list(dates), list(values), time_filter="month")
            self.heatmap.plot_heatmap(processed_data)
            
            self.statusMessage.emit(*StatusMsg.get("ACTIVITY_UPDATED", "Dashboard", "Global"))
              
        except Exception as e:
            traceback.print_exc()
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))

    def _prepare_30_days(self, data):
        """Generuje listę 30 ostatnich dni."""
        end_date = datetime.now().date()
        
        date_map = {}
        if data:
            for d, v in data:
                d_key = d if isinstance(d, str) else d.strftime("%Y-%m-%d")
                date_map[d_key] = v
        
        full_period = []
        # pętla wykona się 30 razy (od 29 do 0 włącznie)
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
            "btn_refresh": "Click to recalculate all community statistics."
        }
        apply_tooltips(self.ui, tooltips)