from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from data.utils.status_manager import StatusMsg
from data.repositories.book_repo import BookRepository
from data.repositories.challenge_repo import ChallengeRepository
from data.repositories.statistics_repo import StatsRepository
from charts.activity_chart import ActivityChart
from data.utils.ui_helpers import load_ui, apply_tooltips

class DashboardView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/DashboardView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI!")
            return

        # Repozytoria
        self.stats_repo = StatsRepository(conn)
        self.book_repo = BookRepository(conn)
        self.challenge_repo = ChallengeRepository(conn)

        # Konfiguracja podpowiedzi (tooltips) przy użyciu helpera
        self.setup_tooltips()

        # Inicjalizacja widoku
        self.ui.btn_refresh.clicked.connect(self.load_view)
        
        self.load_view()

    def setup_tooltips(self):
        """Dodaje podpowiedzi do KPIs po najechaniu kursorem (masowe przypisanie)"""
        tooltips = {
            "lbl_users": "Total registered users and growth (+X) within the last 30 days.",
            "lbl_books": "Number of books marked as 'finished' during the current month.",
            "lbl_pages": "Average daily pages read per active user.",
            "lbl_challenges": "Number of reading challenges currently in progress (status: active).",
            "btn_refresh": "Force refresh of all dashboard statistics and trend charts."
        }
        
        # Wykorzystanie centralnego helpera
        apply_tooltips(self.ui, tooltips)

    def setup_chart(self):
        """Inicjalizuje widget wykresu wewnątrz ramki z UI."""
        if self.ui.verticalLayout_3.count() > 0:
            item = self.ui.verticalLayout_3.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.canvas = ActivityChart(self.ui.frame_chart)
        self.ui.verticalLayout_3.addWidget(self.canvas)

    def load_view(self):
        """Szybkie odświeżanie KPI i wykresu z raportowaniem stanu."""
        try:
            # Pobranie KPI z bazy danych
            user_metrics = self.stats_repo.get_dashboard_metrics()
            total_users, new_users, avg_pages = user_metrics if user_metrics else (0, 0, 0)
            
            books_month = self.book_repo.count_books_read(period="month")
            active_challenges = self.challenge_repo.count_active()

            # Aktualizacja UI
            self.ui.lbl_users.setText(f"Users: {total_users} (+{new_users})")
            self.ui.lbl_books.setText(f"Books read: {books_month or 0}")
            self.ui.lbl_pages.setText(f"Pages / day: {round(avg_pages, 1) if avg_pages else 0}")
            self.ui.lbl_challenges.setText(f"Active challenges: {active_challenges or 0}")

            # Zarządzanie wykresem
            if not hasattr(self, 'canvas'):
                self.setup_chart()

            trend_data = self.book_repo.get_monthly_reading_trend()
            
            # --- LOGIKA STATUSÓW ---
            if trend_data:
                dates = [row[0] for row in trend_data]
                pages = [row[1] for row in trend_data]
                self.canvas.plot_data(dates, pages, time_filter="month")
                
                self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", "Dashboard"))
            else:
                self.statusMessage.emit(*StatusMsg.get("NO_TREND_DATA", "current month"))
              
        except Exception as e:
            # Error: Błąd krytyczny podczas pobierania danych z repozytoriów
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))