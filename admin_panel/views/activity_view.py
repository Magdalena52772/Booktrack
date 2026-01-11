from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QVBoxLayout
from views.dashboard_view import ActivityChart
from data.repositories.activity_repo import ActivityRepository

class ActivityView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Ładowanie interfejsu z pliku .ui
        loader = QUiLoader()
        ui_file = QFile("views/ui/ActivityView.ui")
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)

        self.repo = ActivityRepository(conn)
        
        # Inicjalizacja wykresu
        self.canvas = ActivityChart(self.ui.activity_chart)
        
        # Usunięcie placeholdera i dodanie wykresu do layoutu
        self.ui.verticalLayout_4.replaceWidget(self.ui.lbl_chart_placeholder, self.canvas)
        self.ui.lbl_chart_placeholder.deleteLater()

        # Konfiguracja Tooltipów dla KPI
        self.setup_tooltips()

        # Sygnały
        self.ui.btn_refresh_activity.clicked.connect(self.refresh_data)
        self.ui.cb_time_filter.currentTextChanged.connect(self.refresh_data)

        self.refresh_data()

    def setup_tooltips(self):
        """Dodaje podpowiedzi do KPIs po najechaniu kursorem"""
        self.ui.lbl_books_count.setToolTip(
            "Total number of pages read by all users in the selected period."
        )
        self.ui.lbl_active_days.setToolTip(
            "Number of days with at least one reading session recorded."
        )
        self.ui.lbl_challenges.setToolTip(
            "Average pages read per single session (reading intensity)."
        )

    def refresh_data(self):
        """Pełne odświeżenie widoku i wskaźników."""
        time_filter = self.ui.cb_time_filter.currentText().lower() # Normalizacja do małych liter
        
        # Pobranie KPI z bazy danych
        total_pages, active_days, avg_session = self.repo.get_activity_kpi(time_filter)
        
        # Aktualizacja etykiet
        self.ui.lbl_books_count.setText(f"Total Pages: {total_pages}")
        self.ui.lbl_active_days.setText(f"Active Days: {active_days}")
        self.ui.lbl_challenges.setText(f"Avg Session: {avg_session}")
        
        # Pobranie danych trendu (wykres)
        trend_data = self.repo.get_all_trend(time_filter) if hasattr(self.repo, 'get_all_trend') else self.repo.get_activity_trend(time_filter)
        
        if trend_data:
            dates = [row[0] for row in trend_data]
            pages = [row[1] for row in trend_data]
            # Przekazanie danych do kontrolki wykresu
            self.canvas.plot_data(dates, pages, time_filter=time_filter)
        else:
            # Jeśli brak danych, wyczyść wykres, aby nie pokazywał starej skali
            self.canvas.plot_data([], [], time_filter=time_filter)
        
        self.statusMessage.emit(f"Activity analytics updated ({time_filter})", "info")