from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from data.utils.status_manager import StatusMsg
from data.utils.ui_helpers import apply_tooltips, load_ui
from views.dashboard_view import ActivityChart
from data.repositories.activity_repo import ActivityRepository
from data.repositories.statistics_repo import StatsRepository

class ActivityView(QWidget):
    """
    Widok sekcji Activity. 
    Odpowiada za wizualizację trendów czytelniczych, statystyk KPI 
    oraz rankingu najdłuższych serii (streaks).
    """
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/ActivityView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI!")
            return

        # Inicjalizacja warstwy danych
        self.repo = ActivityRepository(conn)
        self.stats = StatsRepository(conn)
        
        # Konfiguracja komponentu wykresu
        self.canvas = ActivityChart(self.ui.activity_chart)
        
        # Podmiana placeholdera w layoutcie na aktywny wykres Matplotlib
        self.ui.verticalLayout_4.replaceWidget(self.ui.lbl_chart_placeholder, self.canvas)
        self.ui.lbl_chart_placeholder.deleteLater()

        # Definicja podpowiedzi systemowych (Tooltips)
        self.setup_tooltips()

        # Rejestracja zdarzeń i sygnałów interfejsu
        self.ui.btn_refresh_activity.clicked.connect(self.refresh_data)
        self.ui.cb_time_filter.currentTextChanged.connect(self.refresh_data)

    def setup_tooltips(self):
        """Konfiguracja opisów pomocniczych przy użyciu helpera."""
        tooltips = {
            "lbl_books_count": "Total number of pages read by all users in the selected period.",
            "lbl_active_days": "Number of days with at least one reading session recorded.",
            "lbl_streaks": "Current top 3 users with the longest daily reading streaks.",
            "btn_refresh_activity": "Manually refresh all activity statistics and charts.",
            "cb_time_filter": "Select the timeframe for the displayed data."
        }
        
        # Wywołanie funkcji pomocniczej (masowe przypisanie)
        apply_tooltips(self.ui, tooltips)

    def load_view(self):
        """Metoda wywoływana przy aktywacji zakładki w oknie głównym."""
        self.refresh_data()

    def format_top_streaks_html(self, streaks):
        """
        Konwersja danych o rankingach na sformatowany blok HTML.
        Zastosowanie znaczników <br> dla pionowego układu elementów podium.
        """
        if not streaks:
            return "<span style='color: #888;'>No active streaks yet 🔥</span>"

        icons = ["🥇", "🥈", "🥉"]
        formatted_items = []
        
        # Przetwarzanie maksymalnie trzech najlepszych wyników
        for i, (username, days) in enumerate(streaks[:3]):
            icon = icons[i] if i < len(icons) else "🔥"
            # Budowa elementu: Ikona, pod nią Nazwa, pod nią Dni
            entry = (
                f"<div style='text-align: center;'>"
                f"<span style='font-size: 16px;'>{icon}</span><br>"
                f"<b>{username}</b><br>"
                f"<span style='color: #d35400;'>{days} DAYS</span>"
                f"</div>"
            )
            formatted_items.append(entry)
        
        # Łączenie elementów w jeden wiersz z separatorem
        separator = " &nbsp;&nbsp; | &nbsp;&nbsp; "
        return separator.join(formatted_items)

    def refresh_data(self):
        """
        Główna procedura odświeżania danych. 
        Pobiera parametry filtrów, wykonuje zapytania do bazy 
        i aktualizuje komponenty graficzne.
        """
        try:
            # Odczyt aktualnego filtra czasowego
            selected_filter = self.ui.cb_time_filter.currentText()
            time_filter_key = selected_filter.lower()
            
            # Powiadomienie o rozpoczęciu ładowania (angielski tekst statusu)
            self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"Activity ({selected_filter})"))
            
            # Pobranie danych agregowanych (KPI)
            total_pages, active_days, _ = self.repo.get_activity_kpi(time_filter_key)
            
            # Pobranie danych o zaangażowaniu (rankingi)
            engagement = self.stats.get_engagement_stats(time_filter_key)
            
            # Aktualizacja etykiet tekstowych (zachowanie formatu angielskiego)
            self.ui.lbl_books_count.setText(f"Total Pages: {total_pages}")
            self.ui.lbl_active_days.setText(f"Active Days: {active_days}")
            
            # Generowanie i osadzanie rankingu Top 3 w formacie RichText
            streaks_data = engagement.get('top_streaks', [])
            self.ui.lbl_streaks.setText(self.format_top_streaks_html(streaks_data))
            
            # Aktualizacja przebiegu trendu na osi czasu
            trend_data = self.repo.get_activity_trend(time_filter_key)
            if trend_data:
                dates = [row[0] for row in trend_data]
                values = [row[1] for row in trend_data]
                self.canvas.plot_data(dates, values, time_filter=time_filter_key)

        except Exception as e:
            # Rejestracja błędu w pasku statusu aplikacji
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))