from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from views import DashboardView, UsersView, ActivityView, GenresView, ReportsView

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        uic.loadUi("views/ui/MainWindow.ui", self)

        # Ładowanie stylów
        try:
            with open("assets/style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass
            
        # ====== Status Bar ======
        self.status = self.statusBar()
        
        
        # ====== Create views ======
        self.page_dashboard = DashboardView(self.conn)
        self.page_users = UsersView(self.conn)
        self.page_genres = GenresView(self.conn)
        self.page_activity = ActivityView(self.conn)
        self.page_reports = ReportsView(self.conn)

        # ====== Map buttons to pages ======
        self.pages = {
            self.btn_dashboard: self.page_dashboard,
            self.btn_users: self.page_users,
            self.btn_genres: self.page_genres,
            self.btn_activity: self.page_activity,
            self.btn_reports: self.page_reports
        }

        # ====== Add pages and connect buttons ======
        for btn, page in self.pages.items():
            self.ContentArea.addWidget(page)
            btn.clicked.connect(lambda checked, p=page: self.switch_page(p))

            # ====== Emit status message ======
            if hasattr(page, "statusMessage"):
                page.statusMessage.connect(self.show_status_message)
            
        # ====== Obsługa Logout ======
        self.btn_logout.clicked.connect(self.handle_logout)
        self.btn_logout.setToolTip("End session and secure database")

        # Domyślny start
        self.btn_dashboard.setChecked(True)
        self.switch_page(self.page_dashboard)
        self.show_status_message("System ready — logged in as admin.", "success")

    def handle_logout(self):
        """Obsługuje proces wylogowania i zamknięcia sesji."""
        # TODO in future: dodanie funkcji logoutu np. self.auth_service.logout()
        
        confirm = QMessageBox.question(
            self, 
            "Logout", 
            "Are you sure you want to log out and close the session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.show_status_message("Closing session...", "warning")
            # Bezpieczne zamknięcie połączenia przed wyjściem
            self.close()

    def closeEvent(self, event):
        """Zdarzenie wywoływane przy zamykaniu okna (przez X lub Logout)."""
        try:
            # 1. Zatrzymanie generatorów tła (jeśli są przypięte do self)
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            
            # 2. Fizyczne zamknięcie bazy danych
            if self.conn:
                self.conn.close()
                print("Database connection closed securely.")
            
            event.accept()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            event.accept()

    def show_status_message(self, message: str, status_type: str = "info"):
        self.status.setProperty("statusType", status_type)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.showMessage(message, 4000)


    # ====== Page Switch Handler ======
    def switch_page(self, page):
        # change active page
        self.ContentArea.setCurrentWidget(page)
        for btn, p in self.pages.items():
            btn.setChecked(p == page)
        
        if hasattr(page, "load_view"):
            page.load_view()