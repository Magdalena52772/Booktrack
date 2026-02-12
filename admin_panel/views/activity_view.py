# views/activity_view.py
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QVBoxLayout

from data.utils.status_manager import StatusMsg
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

    def load_view(self):
        """Metoda wywoływana przez MainWindow przy przełączaniu zakładki"""
        # Wywołanie odświeżenia danych
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
        """Pełne odświeżenie widoku z jednym, połączonym komunikatem statusu."""
        try:
            # Pobranie tekstu filtra z ComboBox
            selected_filter = self.ui.cb_time_filter.currentText()
            time_filter_key = selected_filter.lower()
            
            # Emisja sygnału informującego o rozpoczęciu przetwarzania danych.
            self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"Activity ({selected_filter})"))
            
            # Pobranie statystyk KPI z repozytorium
            total_pages, active_days, avg_session = self.repo.get_activity_kpi(time_filter_key)
            
            # Aktualizacja etykiet w interfejsie
            self.ui.lbl_books_count.setText(f"Total Pages: {total_pages}")
            self.ui.lbl_active_days.setText(f"Active Days: {active_days}")
            self.ui.lbl_challenges.setText(f"Avg Session: {avg_session} pages")
            
            # Pobranie i rysowanie trendu na wykresie
            trend_data = self.repo.get_activity_trend(time_filter_key)
            if trend_data:
                dates = [row[0] for row in trend_data]
                pages = [row[1] for row in trend_data]
                self.canvas.plot_data(dates, pages, time_filter=time_filter_key)

            # --- SYSTEM STATUS MESSAGE ---
            # Weryfikacja dostępności danych i wybór odpowiedniego szablonu komunikatu.
            if total_pages == 0:
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", selected_filter))
            else:
                # wysłanie zbiorczego komunikatu o sukcesie z wykorzystaniem szablonu ACTIVITY_UPDATED.
                self.statusMessage.emit(*StatusMsg.get("ACTIVITY_UPDATED", selected_filter, total_pages))

        except Exception as e:
            # Obsługa ewentualnych wyjątków
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))