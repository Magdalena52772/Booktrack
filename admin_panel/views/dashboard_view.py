from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QVBoxLayout

from data.repositories.user_repo import UserRepository
from data.repositories.book_repo import BookRepository
from data.repositories.challenge_repo import ChallengeRepository
from charts.activity_chart import ActivityChart

class DashboardView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Ładowanie interfejsu z pliku .ui
        loader = QUiLoader()
        ui_file = QFile("views/ui/DashboardView.ui")
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # Repozytoria
        self.user_repo = UserRepository(conn)
        self.book_repo = BookRepository(conn)
        self.challenge_repo = ChallengeRepository(conn)

        # Konfiguracja podpowiedzi (tooltips)
        self.setup_tooltips()

        # Inicjalizacja widoku
        self.ui.btn_refresh.clicked.connect(self.load_view)
        
        self.load_view()

    def setup_tooltips(self):
        """Dodaje podpowiedzi do KPIs po najechaniu kursorem"""
        self.ui.lbl_users.setToolTip(
            "Total registered users and growth (+X) within the last 30 days."
        )
        self.ui.lbl_books.setToolTip(
            "Number of books marked as 'finished' during the current month."
        )
        self.ui.lbl_pages.setToolTip(
            "Average daily pages read per active user."
        )
        self.ui.lbl_challenges.setToolTip(
            "Number of reading challenges currently in progress (status: active)."
        )

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
            user_metrics = self.user_repo.get_dashboard_metrics()
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
                
                # Info: Wszystko załadowane poprawnie
                self.statusMessage.emit("Dashboard updated: All metrics and trend data loaded.", "info")
            else:
                # Warning: KPI są, ale brak danych do wykresu
                if hasattr(self.ui, 'lbl_activity_chart'):
                    self.ui.lbl_activity_chart.setText("No data over last month.")
                
                msg = "Dashboard KPIs updated, but no trend data available for the current month."
                self.statusMessage.emit(msg, "warning")

        except Exception as e:
            # Error: Błąd krytyczny podczas pobierania danych z repozytoriów
            error_msg = f"Critical error during dashboard refresh: {str(e)}"
            self.statusMessage.emit(error_msg, "error")