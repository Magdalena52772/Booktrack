from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QMainWindow, QMessageBox, QSizePolicy, QVBoxLayout
from views import DashboardView, UsersView, ActivityView, GenresView, ReportsView

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        
        # Inicjalizacja ładowania interfejsu użytkownika
        loader = QUiLoader()
        ui_file = QFile("views/ui/MainWindow.ui")
        
        if not ui_file.open(QFile.ReadOnly):
            return
            
        # Ładowanie interfejsu jako komponentu klasy nadrzędnej
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Osadzenie załadowanego widgetu centralnego w oknie głównym
        if hasattr(self.ui, 'centralwidget'):
            self.setCentralWidget(self.ui.centralwidget)
        else:
            self.setCentralWidget(self.ui)

        # Inicjalizacja poszczególnych widoków aplikacyjnych
        self.page_dashboard = DashboardView(self.conn)
        self.page_users = UsersView(self.conn)
        self.page_genres = GenresView(self.conn)
        self.page_activity = ActivityView(self.conn)
        self.page_reports = ReportsView(self.conn)

        # Mapowanie przycisków na kontenery w QStackedWidget oraz obiekty widoków
        self.pages_map = {
            self.ui.btn_dashboard: (self.ui.page_dashboard, self.page_dashboard),
            self.ui.btn_users: (self.ui.page_users, self.page_users),
            self.ui.btn_genres: (self.ui.page_genres, self.page_genres),
            self.ui.btn_activity: (self.ui.page_activity, self.page_activity),
            self.ui.btn_reports: (self.ui.page_reports, self.page_reports)
        }

        # Konfiguracja layoutów kontenerów i połączeń sygnałów
        for btn, (container, view) in self.pages_map.items():
            # Zapewnienie obecności layoutu w kontenerze strony
            if container.layout() is None:
                layout = QVBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
            
            # Integracja widoku z układem graficznym kontenera
            view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            container.layout().addWidget(view)
            
            # Rejestracja zdarzenia kliknięcia przycisku
            btn.clicked.connect(lambda checked=False, c=container, v=view: self.switch_page(c, v))
            
            if hasattr(view, "statusMessage"):
                view.statusMessage.connect(self.show_status_message)

        # Wczytanie arkuszy stylów i konfiguracja paska stanu
        self.load_styles()
        self.ui.btn_logout.clicked.connect(self.handle_logout)
        self.status = self.statusBar()

        # Konfiguracja parametrów startowych okna
        self.setMinimumSize(1100, 750)
        self.ui.btn_dashboard.setChecked(True)
        self.switch_page(self.ui.page_dashboard, self.page_dashboard)

    def load_styles(self):
        """Wczytywanie definicji stylów QSS z pliku zewnętrznego."""
        try:
            with open("assets/style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def switch_page(self, container, view):
        """Przełączanie aktywnego widoku wewnątrz QStackedWidget."""
        self.ui.ContentArea.setCurrentWidget(container)
        
        # Aktualizacja stanu wizualnego przycisków nawigacyjnych
        for btn in self.pages_map.keys():
            is_active = (btn == self.sender() or self.pages_map[btn][0] == container)
            btn.setChecked(is_active)
        
        # Wywołanie procedur odświeżania danych w widoku
        if hasattr(view, "load_view"):
            view.load_view()
        
        view.updateGeometry()

    def handle_logout(self):
        """Obsługa procedury wylogowania użytkownika."""
        msg = QMessageBox.question(
            self, "Logout", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg == QMessageBox.StandardButton.Yes:
            self.close()

    def show_status_message(self, message: str, status_type: str = "info"):
        """Wyświetlanie komunikatu na pasku stanu aplikacji."""
        self.status.showMessage(message, 4000)

    def closeEvent(self, event):
        """Zwalnianie zasobów i zamykanie połączeń przy wyjściu z aplikacji."""
        if self.conn:
            self.conn.close()
        event.accept()