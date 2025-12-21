from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from views.dashboard_view import ActivityChart
from data.repositories.activity_repo import ActivityRepository

class ActivityView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.repo = ActivityRepository(conn)
        uic.loadUi("views/ui/ActivityView.ui", self)

        # Inicjalizacja wykresu
        self.canvas = ActivityChart(self.activity_chart)
        # Usunięcie placeholdera i dodanie wykresu do layoutu
        self.verticalLayout_4.replaceWidget(self.lbl_chart_placeholder, self.canvas)
        self.lbl_chart_placeholder.deleteLater()

        # Konfiguracja Tooltipów dla KPI
        self.setup_tooltips()

        # Sygnały
        self.btn_refresh_activity.clicked.connect(self.refresh_data)
        self.cb_time_filter.currentTextChanged.connect(self.refresh_data)

        self.refresh_data()

    def setup_tooltips(self):
        """Dodaje podpowiedzi do KPIs po najechaniu kursorem"""
        self.lbl_books_count.setToolTip(
            "Total number of pages read by all users in the selected period."
        )
        self.lbl_active_days.setToolTip(
            "Number of days with at least one reading session recorded."
        )
        self.lbl_challenges.setToolTip(
            "Average pages read per single session (reading intensity)."
        )

    def refresh_data(self):
        """Pełne odświeżenie widoku i wskaźników."""
        time_filter = self.cb_time_filter.currentText()
        
        # Pobranie KPI z nową logiką (Strony, Dni, Średnia)
        total_pages, active_days, avg_session = self.repo.get_activity_kpi(time_filter)
        
        # Aktualizacja etykiet tekstowych
        self.lbl_books_count.setText(f"Total Pages: {total_pages}")
        self.lbl_active_days.setText(f"Active Days: {active_days}")
        self.lbl_challenges.setText(f"Avg Session: {avg_session}")
        
        # Pobranie i odświeżenie złotego wykresu
        trend_data = self.repo.get_activity_trend(time_filter)
        if trend_data:
            dates = [row[0] for row in trend_data]
            pages = [row[1] for row in trend_data]
            # Przekazujemy time_filter, aby zoptymalizować oś X
            self.canvas.plot_data(dates, pages, time_filter=time_filter)
        
        # Logowanie statusu
        self.statusMessage.emit(f"Activity analytics updated ({time_filter})", "info")