from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow, QMessageBox, QSizePolicy, QVBoxLayout
from data.utils.status_manager import StatusMsg
import time
import sys

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        _t_start = time.perf_counter()
        self.conn = conn
        # Flaga do kontrolowania, czy sekwencja startowa została zakończona (używana do optymalizacji sprawdzania aktualizacji podczas startupu)
        self._startup_generation_done = False
        print(f"[TIMING] MainWindow.__init__ START", file=sys.stderr, flush=True)

        # Inicjalizacja ładowania głównego interfejsu użytkownika
        loader = QUiLoader()
        ui_file = QFile("views/ui/MainWindow.ui")
        if not ui_file.open(QFile.ReadOnly):
            return

        print(f"[TIMING] UI file opened: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        self.ui = loader.load(ui_file, self)
        print(f"[TIMING] UI loaded from file: {(time.perf_counter()-_t_start)*1000:.0f}ms")
        ui_file.close()

        # Konfiguracja głównego widgetu okna
        if hasattr(self.ui, 'centralwidget'):
            self.setCentralWidget(self.ui.centralwidget)
        else:
            self.setCentralWidget(self.ui)

        print(f"[TIMING] Central widget set: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        # Konfiguracja mapowania nawigacji (Lazy Loading views)
        # Klasy viewów będą importowane dynamicznie w switch_page()
        self.view_config = {
            self.ui.btn_dashboard: {"class_name": "DashboardView", "container": self.ui.page_dashboard, "instance": None},
            self.ui.btn_users:     {"class_name": "UsersView",     "container": self.ui.page_users,     "instance": None},
            self.ui.btn_genres:    {"class_name": "GenresView",    "container": self.ui.page_genres,    "instance": None},
            self.ui.btn_activity:  {"class_name": "ActivityView",  "container": self.ui.page_activity,  "instance": None},
            self.ui.btn_reports:   {"class_name": "ReportsView",   "container": self.ui.page_reports,   "instance": None},
            self.ui.btn_live_feed: {"class_name": "LiveFeedView", "container": self.ui.page_live_feed, "instance": None}
        }

        print(f"[TIMING] View config created: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        # Rejestracja zdarzeń dla przycisków nawigacyjnych
        for btn in self.view_config.keys():
            btn.clicked.connect(self.handle_navigation)

        print(f"[TIMING] Navigation buttons connected: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        self.load_styles()
        print(f"[TIMING] Styles loaded: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        self.ui.btn_logout.clicked.connect(self.handle_logout)
        self.status = self.statusBar()

        # Parametry startowe okna
        self.setMinimumSize(1100, 750)
        self.ui.btn_dashboard.setChecked(True)

        print(f"[TIMING] MainWindow.__init__ DONE: {(time.perf_counter()-_t_start)*1000:.0f}ms")

        # Opóźnia Dashboard loading (50ms) - Qt wyrenderuje template, potem matplotlib
        # (Preload worker działa w tle, nie blokuje main thread)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._deferred_load_dashboard)

    def _preload_dashboard_data(self):
        """Startuje ładowanie dashboard danych w tle (nie czeka na UI)"""
        # Przechowywuje dane tymczasowo (będą użyte w _on_dashboard_data_loaded)
        self._preloaded_dashboard_data = None

        # Startuje worker
        self._preload_worker = __import__('worker', fromlist=['DatabaseWorker']).DatabaseWorker("load_dashboard", db_connection=self.conn)
        self._preload_worker.finished.connect(self._on_preload_finished)
        self._preload_worker.start()

    def _on_preload_finished(self, data):
        """Callback kiedy preload się skończy"""
        self._preloaded_dashboard_data = data
        from datetime import datetime as dt
        print(f"[TIMING] Dashboard preload FINISHED at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

    def _get_view_class(self, class_name):
        """Importuje view class dynamicznie (lazy loading)"""
        # Mapowanie nazw string'owych na moduły
        view_modules = {
            "DashboardView": ("views.dashboard_view", "DashboardView"),
            "UsersView": ("views.users_view", "UsersView"),
            "GenresView": ("views.genres_view", "GenresView"),
            "ActivityView": ("views.activity_view", "ActivityView"),
            "ReportsView": ("views.reports_view", "ReportsView"),
            "LiveFeedView": ("views.live_feed_view", "LiveFeedView"),
        }

        if class_name in view_modules:
            # Dynamiczny import modułu i klasy
            module_name, class_to_import = view_modules[class_name]
            module = __import__(module_name, fromlist=[class_to_import])
            return getattr(module, class_to_import)
        raise ValueError(f"Unknown view class: {class_name}")

    def handle_navigation(self):
        """Metoda pośrednicząca w obsłudze nawigacji."""
        button = self.sender()
        if config := self.view_config.get(button):
            self.switch_page(config)

    def _deferred_load_dashboard(self):
        """Pokazuje Dashboard view natychmiast z placeholderami, dane ładują się w tle."""
        from datetime import datetime as dt
        print(f"[TIMING] _deferred_load_dashboard START at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

        # Switch page natychmiast pokazuje view z placeholderami
        self.switch_page(self.view_config[self.ui.btn_dashboard])

        # Preload w tle, bez czekania na startup
        self._preload_dashboard_data()

        print(f"[TIMING] _deferred_load_dashboard DONE at {dt.now().strftime('%H:%M:%S.%f')[:-3]}")

    def switch_page(self, config):
        """Zarządzanie przełączaniem stron i leniwą inicjalizacją widoków."""
        container = config["container"]

        # Inicjalizacja widoku przy pierwszym wywołaniu
        if config["instance"] is None:
            # Lazy loading: importuje view class dynamicznie
            view_class = self._get_view_class(config["class_name"])

            # Tworzenie obiektu widoku
            view_instance = view_class(self.conn)
            config["instance"] = view_instance

            # Konfiguracja układu graficznego w kontenerze docelowym
            if container.layout() is None:
                layout = QVBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

            view_instance.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            container.layout().addWidget(view_instance)

            # Rejestracja sygnałów statusu
            if hasattr(view_instance, "statusMessage"):
                view_instance.statusMessage.connect(self.show_status_message)

        # Aktualizacja aktywnego widoku w obszarze ContentArea
        self.ui.ContentArea.setCurrentWidget(container)

        # Aktualizacja stanu wizualnego przycisków (toggle effect)
        for btn, cfg in self.view_config.items():
            btn.setChecked(cfg["container"] == container)

        # Wywołanie metod odświeżania danych
        active_view = config["instance"]
        # Import ReportsView dynamicznie do sprawdzenia typu
        from views.reports_view import ReportsView
        if isinstance(active_view, ReportsView):
            active_view.generate_report()
        elif hasattr(active_view, "load_view"):
            # Opóźnienie load_view() o 1ms, żeby UI zdążyło się odświeżyć
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1, active_view.load_view)

        active_view.updateGeometry()

    def startup_sequence(self):
        """Sekwencja logowania i ładowania ekranu startowego"""

        # odświeżenie UI
        self.show()
        QApplication.processEvents()

        # Wywołanie standardowego przełączenia strony
        dashboard_config = self.view_config[self.ui.btn_dashboard]
        self.switch_page(dashboard_config)

        # Nadpisanie komunikatów ładowania napisem powitalnym
        self.show_status_message("Login success: Welcome, Admin!", StatusMsg.SUCCESS)

    def load_styles(self):
        """Wczytywanie arkuszy stylów QSS."""
        try:
            with open("assets/style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def handle_logout(self):
        """Obsługa zamknięcia aplikacji."""
        confirm = QMessageBox.question(
            self, "Logout", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.close()

    def show_status_message(self, message: str, status_type: str = "info"):
        """Wyświetlanie komunikatów na pasku stanu."""
        self.status.setProperty("statusType", status_type)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.showMessage(message, 5000)

    def closeEvent(self, event):
        """Zamykanie połączeń bazodanowych przy wyjściu."""
        if self.conn:
            self.conn.close()
        event.accept()