from datetime import datetime, timedelta
import traceback
from PySide6.QtCore import Signal, QThread, QTimer, Qt
from PySide6.QtWidgets import QWidget, QSizePolicy
from data.utils.status_manager import StatusMsg
from data.repositories.book_repo import BookRepository
from data.repositories.statistics_repo import StatsRepository
from data.repositories.activity_repo import ActivityRepository
from charts.activity_charts import ActivityChart, ActivityHeatmap
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips, clear_layout
from worker import DatabaseWorker


class ChartRenderWorker(QThread):
    """Przetwarza dane wykresów w tle i zwraca przetworzone pakiety do rysowania na wątku UI.

    Rzeczywiste rysowanie (wywołania do canvas/heatmap) odbywa się na wątku głównym.
    Ten worker wykonuje tylko przetwarzanie ciężkich danych (np. serializację/formatowanie)
    i emituje gotowy payload, który następnie jest rysowany w main thread.
    """

    finished = Signal(object)

    def __init__(self, chart_data):
        super().__init__()
        self.chart_data = chart_data

    def run(self):
        try:
            # Przetwarzanie danych wykresu
            processed = self.chart_data
            # Przygotowanie payloadu do rysowania (rozpakowanie dat i wartości do osobnych list)
            if (
                processed
                and isinstance(processed, (list, tuple))
                and len(processed)
                and isinstance(processed[0], tuple)
            ):
                dates, values = zip(*processed)
                dates_list = list(dates)
                values_list = list(values)
                payload = (dates_list, values_list, processed)
            else:
                # fallback
                payload = ([], [], processed)
            self.finished.emit(payload)
        except Exception:
            # W razie błędu zwraca pusty payload
            try:
                self.finished.emit(([], [], []))
            except Exception:
                pass


class DashboardView(QWidget):
    """Główny panel z dynamicznym skalowaniem i odpowiednim wykorzystaniem przestrzeni
    do prezentacji kluczowych statystyk i trendów czytelniczych"""

    statusMessage = Signal(str, str)
    renderingFinished = Signal()  # Wyemituje się kiedy wykresy się wyrenderują

    def __init__(self, conn):
        super().__init__()
        from datetime import datetime as dt

        t_init = dt.now()
        print(f"[DASHBOARD_INIT] START at {t_init.strftime('%H:%M:%S.%f')[:-3]}")

        self.conn = conn

        # Atrybuty muszą istnieć zanim pokaże loading na starcie
        self.canvas = None
        self.heatmap = None
        self._charts_initialized = False

        # Ładowanie zaktualizowanego UI
        self.ui = load_ui(self, "views/ui/DashboardView.ui")
        if not self.ui:
            return

        # Pokazuje loading od razu po wejściu na widok, zanim dojdą dane i wykresy
        self._set_loading_state(True)

        self.stats_repo = StatsRepository(conn)
        self.book_repo = BookRepository(conn)
        self.activity_repo = ActivityRepository(conn)

        # Obsługa zdarzeń
        self.ui.btn_refresh.clicked.connect(self.load_view)

        self._current_worker = None
        self._is_refreshing = False
        self._last_dashboard_data = None
        self._last_render_signature = None
        self._chart_render_pending = False
        self._chart_worker = None
        self._has_seen_valid_data = False
        self._current_check_worker = None
        self._last_activity_stamp = None
        self._recheck_timer = QTimer(self)
        self._recheck_timer.setSingleShot(True)
        self._recheck_timer.timeout.connect(self._run_background_recheck)

        # Setup charts asynchronicznie na Qt event loop (po pokazaniu UI)
        QTimer.singleShot(0, self._setup_charts_deferred)

        # Załaduje dane dashboardu od razu
        QTimer.singleShot(50, self.load_view)

        print(
            f"[DASHBOARD_INIT] DONE at {dt.now().strftime('%H:%M:%S.%f')[:-3]} ({(dt.now()-t_init).total_seconds()*1000:.0f}ms)"
        )

    def setup_charts(self):
        """Inicjalizacja wykresów z wymuszeniem elastyczności rozmiaru."""
        if (
            self._charts_initialized
            and self.canvas is not None
            and self.heatmap is not None
        ):
            return

        # Wykres Trendu
        self.canvas = ActivityChart(self.ui.frame_chart)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(240)
        clear_layout(self.ui.verticalLayout_3)
        self.ui.verticalLayout_3.addWidget(self.canvas)
        if hasattr(self.ui, "lbl_activity_chart"):
            self.ui.lbl_activity_chart = None
        try:
            self.canvas.updateGeometry()
            if hasattr(self.ui, "frame_chart"):
                self.ui.frame_chart.update()
            self.canvas.draw()
        except Exception:
            pass

        # Heatmapa (30 kafli)
        self.heatmap = ActivityHeatmap(self.ui.heatmap_container)
        self.heatmap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.heatmap.setMinimumHeight(200)
        clear_layout(self.ui.verticalLayout_heatmap)
        self.ui.verticalLayout_heatmap.addWidget(self.heatmap)
        if hasattr(self.ui, "lbl_heatmap_placeholder"):
            self.ui.lbl_heatmap_placeholder = None
        try:
            self.heatmap.updateGeometry()
            if hasattr(self.ui, "heatmap_container"):
                self.ui.heatmap_container.update()
            self.heatmap.draw()
        except Exception:
            pass

        self._charts_initialized = True

    def _setup_charts_deferred(self):
        """Setup charts w tle po pokazaniu UI (nie blokuje startup)."""
        from datetime import datetime as dt

        print(
            f"[DASHBOARD_CHARTS] SETUP START at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )
        self.setup_charts()
        self.setup_tooltips()
        print(
            f"[DASHBOARD_CHARTS] SETUP DONE at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )

    def load_view(self):
        """Załaduje dane Dashboard'a w tle (worker thread) — pokazuje placeholdery natychmiast."""
        # Jeśli refresh już trwa i są poprzednie dane, nie resetuje widoku ponownie
        if self._is_refreshing and self._last_dashboard_data:
            print(
                "[TIMING] Dashboard refresh already in progress - keeping current data"
            )
            return

        from datetime import datetime as dt

        print(
            f"[TIMING] Dashboard.load_view() started at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )

        # Safety check - jeśli charts nie istnieją, trigger setup
        if self.canvas is None or self.heatmap is None:
            print("[WARNING] Charts missing on load_view(), re-initializing...")
            self.setup_charts()

        # Pokaże placeholdery natychmiast, zanim worker załaduje dane
        if not self._has_seen_valid_data:
            self._set_loading_state(True)

        # Jeśli dane są już preloaded (z MainWindow), użyje ich natychmiast (stale-while-refresh),
        # ale zawsze triggeruje odświeżenie w tle, żeby mieć aktualne dane po starcie.
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, "_preloaded_dashboard_data"):
            parent_window = parent_window.parent()

        preloaded = None
        if (
            parent_window
            and hasattr(parent_window, "_preloaded_dashboard_data")
            and parent_window._preloaded_dashboard_data
        ):
            # Sprawdzenie czy preloaded zawiera rzeczywiste dane (nie jest pusty lub zerowy)
            preloaded_data = parent_window._preloaded_dashboard_data
            has_real_data = (
                preloaded_data.get("total_users", 0) > 0
                or preloaded_data.get("books_month", 0) > 0
                or len(preloaded_data.get("activity_data", [])) > 0
            )
            if has_real_data:
                preloaded = preloaded_data

        # Jeśli już jest cached dane, pokaże je (stale-while-refresh)
        if self._last_dashboard_data:
            self._update_dashboard_ui(self._last_dashboard_data)
        elif preloaded:
            print(f"[TIMING] Using preloaded dashboard data (has real data)")
            self._on_dashboard_data_loaded(preloaded)

        # Odświeżenie zawsze w tle, bez czekania na startup
        if not self._is_refreshing:
            self._is_refreshing = True
            self._current_worker = DatabaseWorker(
                "load_dashboard", db_connection=self.conn
            )
            try:
                self._current_worker.setParent(self)
            except Exception:
                pass
            self._current_worker.finished.connect(self._on_dashboard_data_loaded)
            self._current_worker.error.connect(self._on_dashboard_error)
            self._current_worker.start()

    def _on_dashboard_data_loaded(self, data):
        """Callback gdy worker załaduje dane."""
        self._is_refreshing = False
        from datetime import datetime as dt

        print(
            f"[TIMING] Dashboard data received at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )
        try:
            if data:
                # Dodatkowa walidacja: sprawdzenie, czy dane zawierają rzeczywiste wartości (nie są puste lub zerowe), zanim pokaże je na UI.
                total_users = data.get("total_users", 0)
                books_month = data.get("books_month", 0)
                activity_data = data.get("activity_data", []) or []

                # Jeśli nie ma użytkowników i nie ma książek, to baza jest pusta
                if total_users == 0 and books_month == 0:
                    print("[TIMING] Worker returned zero users and books - keeping placeholder")
                    self._set_loading_state(True)
                    self._schedule_background_recheck_if_needed()
                    return

                new_signature = self._make_dashboard_signature(data)
                if new_signature != self._last_render_signature:
                    self._last_dashboard_data = data
                    self._last_render_signature = new_signature
                    self._update_dashboard_ui(data)
                    # Ustawia flagę, że pokazały się już ważne dane, więc przy kolejnych
                    # odświeżeniach można pokazywać placeholdery tylko dla wykresów, a nie dla całego UI.
                    self._has_seen_valid_data = True
                    self.statusMessage.emit(
                        *StatusMsg.get("ACTIVITY_UPDATED", "Dashboard", "Global")
                    )
                else:
                    print("[TIMING] Dashboard data unchanged - skipping redraw")
            else:
                # Jeśli backend zwrócił None lub pusty wynik
                if not self._last_dashboard_data:
                    self._update_dashboard_ui({})
            self._set_loading_state(False)
            self._schedule_background_recheck_if_needed()
        except Exception as e:
            traceback.print_exc()
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))
            if not self._last_dashboard_data:
                self._update_dashboard_ui({})
            self._set_loading_state(False)
            self._schedule_background_recheck_if_needed()

    def _on_dashboard_error(self, error_msg):
        """Callback gdy worker napotka błąd."""
        self._is_refreshing = False

        print("\n" + "!" * 60)
        print(f"[CRITICAL REPO ERROR] Błąd bazy danych w DashboardView:")
        print(f"Treść błędu: {error_msg}")
        print("!" * 60 + "\n")

        self.statusMessage.emit(*StatusMsg.get("DB_ERROR", error_msg))
        if not self._last_dashboard_data:
            self._update_dashboard_ui({})
        self._set_loading_state(False)
        self._schedule_background_recheck_if_needed()

    def _find_main_window(self):
        # Pomocnicza metoda do znalezienia MainWindow (aby sprawdzić status generowania danych przy starcie)
        parent_window = self.parent()
        while parent_window and not hasattr(
            parent_window, "_startup_generation_done"
        ):
            parent_window = parent_window.parent()
        return parent_window

    def _is_startup_generation_in_progress(self):
        """Zwraca True, gdy aplikacja nadal generuje startową bazę danych."""
        main_window = self._find_main_window()
        return bool(main_window) and not getattr(
            main_window, "_startup_generation_done", True
        )

    def _schedule_background_recheck_if_needed(self):
        """Uruchamia lekkie sprawdzanie co pół sekundy, aby wykryć zmiany w aktywności."""
        # Jeśli timer już działa, nie restartuje go ponownie
        if self._recheck_timer.isActive():
            return

        # Uruchamia timer — zawsze, niezależnie od startupu
        self._recheck_timer.start(500)

    def _run_background_recheck(self):
        """Uruchamia lekkie sprawdzanie w tle, aby zobaczyć, czy ostatnia aktywność się zmieniła
        (co oznacza, że symulacja zakończyła się) i wtedy triggeruje pełne przeładowanie dashboardu.
        Ten mechanizm jest używany podczas startupu, aby automatycznie odświeżyć dashboard,
        gdy dane staną się dostępne, bez konieczności ręcznego klikania "Refresh".
        """
        if self._is_refreshing:
            return

        # Unika uruchamiania wielu workerów do sprawdzania aktywności - jeśli już jest jeden aktywny, nie startuje kolejnego
        if self._current_check_worker and getattr(
            self._current_check_worker, "isRunning", lambda: False
        )():
            return

        # Uruchamia lekkiego worker'a, który sprawdzi ostatni timestamp aktywności z tabeli meta (string)
        # i porówna go z self._last_activity_stamp. Jeśli jest inny, triggeruje load_view() do pełnego przeładowania danych.
        self._current_check_worker = DatabaseWorker(
            "check_activity_latest", db_connection=self.conn
        )
        try:
            self._current_check_worker.setParent(self)
        except Exception:
            pass
        self._current_check_worker.finished.connect(self._on_check_activity_done)
        self._current_check_worker.error.connect(self._on_dashboard_error)
        self._current_check_worker.start()

    def _on_check_activity_done(self, latest_stamp):
        """Callback kiedy lekki worker sprawdzający ostatnią aktywność zwróci wynik."""
        try:
            if latest_stamp and latest_stamp != self._last_activity_stamp:
                self._last_activity_stamp = latest_stamp
                # Zmiana w aktywności — triggeruje refresh
                if not self._is_refreshing:
                    self.load_view()
            else:
                # Brak zmiany — czeka i spróbuje ponownie
                if not self._recheck_timer.isActive():
                    self._recheck_timer.start(500)
        finally:
            self._current_check_worker = None

    def _update_dashboard_ui(self, data):
        """Aktualizuje UI z załadowanymi danymi."""
        if not data:
            if not self._last_dashboard_data:
                self._set_loading_state(True)
            return

        total_users = data.get("total_users", 0)
        new_users = data.get("new_users", 0)
        avg_pages = data.get("avg_pages", 0)
        books_month = data.get("books_month", 0)
        top_3_streaks = data.get("top_3_streaks", [])
        activity_data = data.get("activity_data", [])

        # Formatowanie tekstu
        accent = "#daa520"
        style = f"color:{accent}; font-weight:bold; font-size:16pt;"
        users_text = (
            f"{total_users}"
            if new_users == 0
            else f"{total_users}<span style='font-size:11pt; color:#90ee90;'>(+{new_users})</span>"
        )
        self.ui.lbl_users.setText(
            f"Users: <br><span style='{style}'>{users_text}</span>"
        )
        self.ui.lbl_books.setText(
            f"Books read: <br><span style='{style}'>{books_month or 0}</span>"
        )
        self.ui.lbl_pages.setText(
            f"Pages / day: <br><span style='{style}'>{round(avg_pages, 1)}</span>"
        )

        # Top 3 streaks
        streak_text = "<span style='font-size:11pt;'><b>Top Streaks:</b><br>"
        for i, (username, streak) in enumerate(top_3_streaks, 1):
            streak_text += f"{i}. {username} ({streak}d)<br>"
        streak_text += "</span>"
        self.ui.lbl_streak.setText(streak_text)

        # Aktualizacja wykresów: pokaże placeholder natychmiast i przetworzy dane w tle
        processed_data = self._prepare_30_days(activity_data)
        if processed_data:
            # Jeśli nie było jeszcze widocznych danych, pokazuje placeholder natychmiast
            if not self._has_seen_valid_data:
                self._set_loading_state(True, charts_only=True)

            # Debounce: nie uruchamia wielu równoległych workerów do renderu
            if self._chart_worker and getattr(
                self._chart_worker, "isRunning", lambda: False
            )():
                print("[TIMING] Chart worker already running - skipping spawn")
            else:
                # Uruchamia worker, który przygotuje payload do rysowania
                self._chart_worker = ChartRenderWorker(processed_data)

                def _on_chart_payload_ready(payload):
                    try:
                        dates_list, values_list, processed = payload
                        # Rysowanie już na wątku UI
                        try:
                            self.canvas.plot_data(
                                list(dates_list),
                                list(values_list),
                                time_filter="month",
                            )
                            self.heatmap.plot_heatmap(processed)
                        except Exception:
                            pass
                        self._on_charts_rendered()
                    finally:
                        self._chart_worker = None

                self._chart_worker.finished.connect(_on_chart_payload_ready)
                self._chart_worker.start()

        from datetime import datetime as dt

        print(
            f"[TIMING] Dashboard UI fully rendered at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )

    def _on_charts_rendered(self):
        """Callback kiedy wykresy się wyrenderują w tle"""
        from datetime import datetime as dt

        print(
            f"[DASHBOARD_READY] Charts fully rendered at {dt.now().strftime('%H:%M:%S.%f')[:-3]}"
        )
        self.renderingFinished.emit()

    def _set_loading_state(self, is_loading, charts_only: bool = False):
        """Pokazuje/ukrywa loading state z placeholderem

        Jeśli `charts_only` jest True, nie modyfikuje metryk (Users/Books/Pages),
        pokazuje tylko placeholdery wykresów — używane przy odświeżeniu kiedy
        są już istniejące dane
        """
        if is_loading:
            loading_style = "color: #999; font-style: italic;"
            if not charts_only:
                # Loading placeholders dla metryk (tylko gdy full loading)
                try:
                    self.ui.lbl_users.setText(
                        f"<span style='{loading_style}'>[LOADING...]</span>"
                    )
                    self.ui.lbl_books.setText(
                        f"<span style='{loading_style}'>[LOADING...]</span>"
                    )
                    self.ui.lbl_pages.setText(
                        f"<span style='{loading_style}'>[LOADING...]</span>"
                    )
                    self.ui.lbl_streak.setText(
                        f"<span style='{loading_style}'>[LOADING...]</span>"
                    )
                except RuntimeError:
                    # QLabel mogło zostać usunięte; ignoruje błędy związane z aktualizacją UI,
                    # które mogą wystąpić podczas szybkiego przełączania widoków
                    pass

            # Pokazuje placeholdery wykresów zanim zostaną podmienione na canvasy matplotlib
            lbl_activity = getattr(self.ui, "lbl_activity_chart", None)
            if lbl_activity is not None:
                try:
                    lbl_activity.setText("[LOADING CHART DATA...]")
                    lbl_activity.setAlignment(Qt.AlignCenter)
                except RuntimeError:
                    pass

            lbl_heatmap = getattr(self.ui, "lbl_heatmap_placeholder", None)
            if lbl_heatmap is not None:
                try:
                    lbl_heatmap.setText("[LOADING HEATMAP...]")
                    lbl_heatmap.setAlignment(Qt.AlignCenter)
                except RuntimeError:
                    pass

            # Placeholder dla wykresów (tylko jeśli canvas już się zainicjalizował)
            canvas = getattr(self, "canvas", None)
            if canvas and getattr(canvas, "axes", None):
                try:
                    canvas.axes.clear()
                    canvas.axes.text(
                        0.5,
                        0.5,
                        "[LOADING CHART DATA...]",
                        ha="center",
                        va="center",
                        fontsize=12,
                        color="#999",
                        style="italic",
                        transform=canvas.axes.transAxes,
                    )
                    canvas.draw()
                except Exception:
                    pass

            heatmap = getattr(self, "heatmap", None)
            if heatmap and getattr(heatmap, "axes", None):
                try:
                    heatmap.axes.clear()
                    heatmap.axes.text(
                        0.5,
                        0.5,
                        "[LOADING HEATMAP...]",
                        ha="center",
                        va="center",
                        fontsize=12,
                        color="#999",
                        style="italic",
                        transform=heatmap.axes.transAxes,
                    )
                    heatmap.draw()
                except Exception:
                    pass
        else:
            # Loading state ukryty - UI będzie aktualizowany przez _update_dashboard_ui()
            try:
                # Resetuje placeholdery, ale tylko jeśli nie było jeszcze ważnych danych (przy pierwszym załadowaniu)
                pass
            except Exception:
                pass

    def _make_dashboard_signature(self, data):
        """Tworzy lekki podpis danych, żeby wykryć realną zmianę przed redraw."""
        if not data:
            return None

        activity_data = data.get("activity_data", []) or []
        top_3_streaks = data.get("top_3_streaks", []) or []

        return (
            data.get("total_users", 0),
            data.get("new_users", 0),
            data.get("avg_pages", 0),
            data.get("books_month", 0),
            tuple(top_3_streaks),
            tuple(activity_data),
        )

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
        """Definiowanie podpowiedzi dla elementów interfejsu."""
        tooltips = {
            "lbl_users": "Total registered users and growth (+X) within the last 30 days.",
            "lbl_books": "Number of books finished this month across the whole community.",
            "lbl_pages": "Average pages read daily per active user.",
            "lbl_streak": "Top 3 users with the longest reading streaks.",
            "btn_refresh": "Click to recalculate all community statistics.",
        }
        apply_tooltips(self.ui, tooltips)