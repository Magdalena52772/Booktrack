from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from data.repositories.activity_repo import ActivityRepository

class ActivityView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.repo = ActivityRepository(conn)

        uic.loadUi("views/ui/ActivityView.ui", self)

        # podłączenie przycisku odświeżania
        self.btn_refresh_activity.clicked.connect(self.refresh_kpi)

        # opcjonalnie można od razu załadować widok
        self.refresh_kpi()

    def load_view(self):
        self.statusMessage.emit("Activity view loaded.", "info")
        self.refresh_kpi()

    def refresh_kpi(self):
        # pobranie aktualnie wybranego filtra czasu
        time_filter = self.cb_time_filter.currentText()
        
        # pobranie KPI z repozytorium
        books, active_days, challenges = self.repo.get_activity_kpi(time_filter)
        
        # aktualizacja UI
        self.lbl_books_count.setText(f"Books: {books}")
        self.lbl_active_days.setText(f"Active days: {active_days}")
        self.lbl_challenges.setText(f"Challenges: {challenges}")
        
        # sygnał statusu
        self.statusMessage.emit("Activity data refreshed.", "info")