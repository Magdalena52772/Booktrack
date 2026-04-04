from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QListWidgetItem

from data.utils.status_manager import StatusMsg
from data.repositories.statistics_repo import StatsRepository
from data.utils.ui_helpers import load_ui, apply_tooltips

class LiveFeedView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/LiveFeedView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI LiveFeed!")
            return

        # Repozytoria
        self.stats_repo = StatsRepository(conn)

        # Konfiguracja
        self.setup_tooltips()
        
        # Sygnały
        self.ui.btn_refresh_live.clicked.connect(self.load_view)
        
        # Inicjalizacja danych
        self.load_view()

    def setup_tooltips(self):
        """Podpowiedzi dla sekcji Live Feed."""
        tooltips = {
            "frame_streaks": "Top 3 users with the highest consecutive reading days.",
            "frame_clusters": "Future AI module: grouping users by reading patterns.",
            "list_events": "Real-time log of recent database changes and user actions.",
            "btn_refresh_live": "Manually refresh streaks and event log."
        }
        apply_tooltips(self.ui, tooltips)

    def load_view(self):
        """Odświeża wszystkie sekcje widoku Live Feed."""
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Live Feed"))
        try:
            self.refresh_streaks()
            self.refresh_event_log()
            self.update_clustering_status()
            
            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", "Live Feed"))
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))

    def refresh_streaks(self):
        """Pobiera i wyświetla Top 3 najdłuższe serie."""
        # Zakładamy, że repozytorium zwraca listę słowników: [{'username': '...', 'streak': 10}, ...]
        top_streaks = self.stats_repo.get_top_streaks(limit=3)
        
        # Reset labeli na wypadek braku danych
        for i in range(1, 4):
            getattr(self.ui, f"lbl_streak_{i}_val").setText("🔥 --")
            getattr(self.ui, f"lbl_streak_{i}_user").setText("No data")

        for i, data in enumerate(top_streaks):
            index = i + 1
            val_label = getattr(self.ui, f"lbl_streak_{index}_val")
            user_label = getattr(self.ui, f"lbl_streak_{index}_user")
            
            val_label.setText(f"🔥 {data['streak']} Days")
            user_label.setText(data['username'])
            
            # Subtelne wyróżnienie pierwszego miejsca
            if index == 1:
                val_label.setStyleSheet("font-weight: bold; color: #e67e22; font-size: 14pt;")

    def refresh_event_log(self):
        """Ładuje ostatnie zdarzenia do listy."""
        self.ui.list_events.clear()
        
        # Tutaj docelowo pobierasz dane z tabeli logów/eventów
        # Przykładowe dane testowe:
        events = [
            "User 'ReadMaster' finished 'The Witcher'",
            "New challenge 'Summer 2026' created",
            "System backup completed successfully",
            "Clustering engine initialized"
        ]
        
        for event in events:
            item = QListWidgetItem(f"ℹ️ {event}")
            self.ui.list_events.addItem(item)

    def update_clustering_status(self):
        """Miejsce na logikę przyszłej klasteryzacji."""
        self.ui.lbl_cluster_info.setText(
            "Gathering data points for K-Means analysis... \n"
            "Status: [Pending]"
        )
        self.ui.lbl_cluster_info.setStyleSheet("color: #7f8c8d; font-style: italic;")

    def add_log_entry(self, message):
        """Publiczna metoda do dodawania logów w czasie rzeczywistym z innych części aplikacji."""
        self.ui.list_events.insertItem(0, f"🔔 {message}")