import traceback
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from data.utils.status_manager import StatusMsg
from data.utils.helpers.ui_helpers import apply_tooltips, load_ui
from charts.activity_charts import ActivityChart
from data.repositories.activity_repo import ActivityRepository
from data.repositories.challenge_repo import ChallengeRepository

class ActivityView(QWidget):
    """Widok analityczny z wykresem trendu i kluczowymi wskaźnikami aktywności."""
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Inicjalizacja interfejsu użytkownika
        self.ui = load_ui(self, "views/ui/ActivityView.ui")
        if not self.ui: return

        # Inicjalizacja repozytoriów danych
        self.repo = ActivityRepository(conn)
        self.challenge_repo = ChallengeRepository(conn)
        
        # Konfiguracja i osadzenie wykresu aktywności
        self.canvas = ActivityChart(self.ui.activity_chart)
        if hasattr(self.ui, 'lbl_chart_placeholder'):
            self.ui.verticalLayout_4.replaceWidget(self.ui.lbl_chart_placeholder, self.canvas)
            self.ui.lbl_chart_placeholder.deleteLater()
        else:
            self.ui.verticalLayout_4.addWidget(self.canvas)

        # Podpięcie zdarzeń przycisków i filtrów
        self.ui.btn_refresh_activity.clicked.connect(self.refresh_data)
        self.ui.cb_time_filter.currentTextChanged.connect(self.refresh_data)

        # Konfiguracja podpowiedzi i ładowanie danych
        self.setup_tooltips()
        self.refresh_data()

    def refresh_data(self):
        """Odświeżanie danych i kluczowych wskaźników."""
        try:
            # Pobranie parametrów filtra czasowego
            selected_filter = self.ui.cb_time_filter.currentText().lower()
            self.statusMessage.emit(*StatusMsg.get("LOAD_START", selected_filter))

            # Pozyskanie danych trendu historycznego
            trend_data = self.repo.get_activity_trend(selected_filter)

            # Pobranie kluczowych wskaźników wydajności (KPI)
            total_pages, real_active_days = self.repo.get_activity_kpi_core(selected_filter)
            unique_readers = self.repo.get_unique_active_users(selected_filter)
            active_challenges = self.challenge_repo.count_active()

            # Aktualizacja komponentów wizualnych
            if trend_data:
                dates, values = zip(*trend_data)
                self.canvas.plot_data(list(dates), list(values), time_filter=selected_filter)

                # Odświeżenie etykiet w panelu bocznym
                self.ui.lbl_books_count.setText(f"Total pages:<br><b style='color:#daa520; font-size:14pt;'>{total_pages:,}</b>")
                self.ui.lbl_active_days.setText(f"Active days:<br><b style='color:#daa520; font-size:14pt;'>{real_active_days}</b>")
                self.ui.lbl_challenges.setText(f"Active challenges:<br><b style='color:#daa520; font-size:14pt;'>{active_challenges or 0}</b>")

                # Aktualizacja dolnego podsumowania
                self._update_summary(trend_data, unique_readers)
                
                # Status sukcesu z użyciem Twojego helpera
                self.statusMessage.emit(*StatusMsg.get("ACTIVITY_UPDATED", selected_filter, f"{total_pages:,} pages"))
            else:
                self._clear_view()
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", selected_filter))

        except Exception as e:
            # Obsługa błędów bazy danych
            traceback.print_exc()
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))

    def _update_summary(self, trend_data, unique_readers):
        """Podsumowanie kluczowych wskaźników w formie HTML."""
        try:
            # Pobranie wartości szczytowej
            peak_data = self.repo.get_peak_activity(trend_data)
            peak_val = peak_data[0] if isinstance(peak_data, (tuple, list)) else peak_data

            accent_color = "#b8860b"

            # Wymuszenie widoczności panelu podsumowania
            self.ui.lbl_summary_placeholder.setMinimumHeight(100)

            # Renderowanie HTML
            summary_html = (
                f"<div style='background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px;'>"
                f"<table width='100%' style='font-family: Segoe UI, sans-serif;'>"
                f"<tr>"
                f"<td align='center' width='50%'>"
                f"<span style='color: #666; font-size: 10pt; text-transform: uppercase;'>🏆 Peak Record</span><br>"
                f"<span style='color: {accent_color}; font-size: 20pt; font-weight: bold;'>{peak_val:,}</span> "
                f"<span style='color: {accent_color}; font-size: 12pt;'>pages</span>"
                f"</td>"
                f"<td width='1' style='background-color: #eee;'></td>"
                f"<td align='center' width='50%'>"
                f"<span style='color: #666; font-size: 10pt; text-transform: uppercase;'>👥 Unique Readers</span><br>"
                f"<span style='color: {accent_color}; font-size: 20pt; font-weight: bold;'>{unique_readers:,}</span> "
                f"<span style='color: {accent_color}; font-size: 12pt;'>users</span>"
                f"</td>"
                f"</tr>"
                f"</table>"
                f"</div>"
            )
            
            self.ui.lbl_summary_placeholder.setText(summary_html)
        except Exception as e:
            print(f"Summary UI Error: {e}")

    def _clear_view(self):
        """Czyści wykres i etykiety w przypadku braku danych."""
        self.canvas.axes.clear()
        self.canvas.draw()
        self.ui.lbl_summary_placeholder.setText("No activity found for this period.")

    def setup_tooltips(self):
        """Definicja podpowiedzi interfejsu."""
        tooltips = {
            "lbl_books_count": "Sum of all pages logged in this period.",
            "lbl_active_days": "Number of unique days with activity in the database.",
            "lbl_challenges": "Current community challenges count.",
            "btn_refresh_activity": "Reload data from database.",
            "lbl_summary_placeholder": "Key performance indicators for selected timeframe."
        }
        apply_tooltips(self.ui, tooltips)