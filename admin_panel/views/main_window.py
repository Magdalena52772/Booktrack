from PyQt6 import uic
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from views import DashboardView, UsersView, ActivityView, GenresView, ReportsView

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        uic.loadUi("views/ui/MainWindow.ui", self)

        with open("assets/style.qss", "r") as f:
            self.setStyleSheet(f.read())
            
        # ====== Status Bar ======
        self.status = self.statusBar()
        
        # ====== Predefined messages ======
        self.messages = {
            "data_loaded": ("Data refreshed successfully.", "success"),
            "data_failed": ("Failed to load data.", "error"),
            "report_ready": ("Report generated successfully.", "success"),
            "report_error": ("Report generation failed.", "error"),
            "no_results": ("No matching results found.", "warning"),
            "connection_lost": ("Connection to database lost.", "error"),
            "reconnected": ("Connection reestablished.", "success")
        }
        
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
            
        self.btn_dashboard.setChecked(True)
        self.switch_page(self.page_dashboard)

        # ====== First message ======
        self.show_status_message("System ready — logged in as admin.", "success")

        
    # ====== Status Bar msg handler ======
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