from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from data.repositories.user_repo import UserRepository
from data.repositories.book_repo import BookRepository
from data.repositories.challenge_repo import ChallengeRepository
from charts.activity_chart import ActivityChart

class DashboardView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        uic.loadUi("views/ui/DashboardView.ui", self)
        self.conn = conn

        # Repozytoria
        self.user_repo = UserRepository(conn)
        self.book_repo = BookRepository(conn)
        self.challenge_repo = ChallengeRepository(conn)

        # Konfiguracja podpowiedzi (tooltips)
        self.setup_tooltips()

        # Inicjalizacja widoku
        self.btn_refresh.clicked.connect(self.load_view)
        
        self.load_view()

    def setup_tooltips(self):
        """Dodaje podpowiedzi do KPIs po najechaniu kursorem"""
        self.lbl_users.setToolTip(
            "Total registered users and growth (+X) within the last 30 days."
        )
        self.lbl_books.setToolTip(
            "Number of books marked as 'finished' during the current month."
        )
        self.lbl_pages.setToolTip(
            "Average daily pages read per active user."
        )
        self.lbl_challenges.setToolTip(
            "Number of reading challenges currently in progress (status: active)."
        )

    def setup_chart(self):
        """Inicjalizuje widget wykresu wewnątrz ramki z UI."""
        if self.verticalLayout_3.count() > 0:
            item = self.verticalLayout_3.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.canvas = ActivityChart(self.frame_chart)
        self.verticalLayout_3.addWidget(self.canvas)

    def load_view(self):
        """Szybkie odświeżanie KPI i wykresu."""
        # Pobranie KPI z bazy
        total_users, new_users, avg_pages = self.user_repo.get_dashboard_metrics()
        books_month = self.book_repo.count_books_read(period="month")
        active_challenges = self.challenge_repo.count_active()

        # Aktualizacja UI
        self.lbl_users.setText(f"Users: {total_users or 0} (+{new_users or 0})")
        self.lbl_books.setText(f"Books read: {books_month or 0}")
        self.lbl_pages.setText(f"Pages / day: {round(avg_pages, 1) if avg_pages else 0}")
        self.lbl_challenges.setText(f"Active challenges: {active_challenges or 0}")

        # Zarządzanie wykresem
        if not hasattr(self, 'canvas'):
            self.setup_chart()

        trend_data = self.book_repo.get_monthly_reading_trend()
        
        if trend_data:
            dates = [row[0] for row in trend_data]
            pages = [row[1] for row in trend_data]
            # Użycie parametru time_filter="month" dla optymalizacji osi X
            self.canvas.plot_data(dates, pages, time_filter="month")
        else:
            # W przypadku braku danych, wyświetla komunikat w miejscu wykresu
            if hasattr(self, 'lbl_activity_chart'):
                self.lbl_activity_chart.setText("No data over last month.")

        self.statusMessage.emit("Dashboard metrics and chart updated.", "info")