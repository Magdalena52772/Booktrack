from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow, QMessageBox, QSizePolicy, QVBoxLayout
from views import DashboardView, UsersView, ActivityView, GenresView, ReportsView, LiveFeedView
from data.utils.status_manager import StatusMsg

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        
        # Inicjalizacja ładowania głównego interfejsu użytkownika
        loader = QUiLoader()
        ui_file = QFile("views/ui/MainWindow.ui")
        if not ui_file.open(QFile.ReadOnly):
            return
            
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Konfiguracja głównego widgetu okna
        if hasattr(self.ui, 'centralwidget'):
            self.setCentralWidget(self.ui.centralwidget)
        else:
            self.setCentralWidget(self.ui)

        # Konfiguracja mapowania nawigacji (Lazy Loading)
        self.view_config = {
            self.ui.btn_dashboard: {"class": DashboardView, "container": self.ui.page_dashboard, "instance": None},
            self.ui.btn_users:     {"class": UsersView,     "container": self.ui.page_users,     "instance": None},
            self.ui.btn_genres:    {"class": GenresView,    "container": self.ui.page_genres,    "instance": None},
            self.ui.btn_activity:  {"class": ActivityView,  "container": self.ui.page_activity,  "instance": None},
            self.ui.btn_reports:   {"class": ReportsView,   "container": self.ui.page_reports,   "instance": None},
            self.ui.btn_live_feed: {"class": LiveFeedView, "container": self.ui.page_live_feed, "instance": None}
        }

        # Rejestracja zdarzeń dla przycisków nawigacyjnych
        for btn in self.view_config.keys():
            btn.clicked.connect(self.handle_navigation)

        self.load_styles()
        self.ui.btn_logout.clicked.connect(self.handle_logout)
        self.status = self.statusBar()

        # Parametry startowe okna
        self.setMinimumSize(1100, 750)
        self.ui.btn_dashboard.setChecked(True)

    def handle_navigation(self):
        """Metoda pośrednicząca w obsłudze nawigacji."""
        button = self.sender()
        if config := self.view_config.get(button):
            self.switch_page(config)

    def switch_page(self, config):
        """Zarządzanie przełączaniem stron i leniwą inicjalizacją widoków."""
        container = config["container"]
        
        # Inicjalizacja widoku przy pierwszym wywołaniu
        if config["instance"] is None:
            view_class = config["class"]
            
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
        if isinstance(active_view, ReportsView):
            active_view.generate_report()
        elif hasattr(active_view, "load_view"):
            active_view.load_view()
        
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