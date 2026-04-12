from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QListWidgetItem
from datetime import datetime

from data.utils.status_manager import StatusMsg
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips

class LiveFeedView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/LiveFeedView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI LiveFeed!")
            return

        # Konfiguracja
        self.setup_tooltips()
        
        # Sygnały
        self.ui.btn_refresh_live.clicked.connect(self.load_view)
        
        # Inicjalizacja danych
        self.load_view()

    def setup_tooltips(self):
        """Podpowiedzi dla sekcji Live Feed."""
        tooltips = {
            "frame_clusters": "Future AI module: grouping users by reading patterns.",
            "list_events": "Real-time log of recent database changes and user actions.",
            "btn_refresh_live": "Manually refresh to see the latest events."
        }
        apply_tooltips(self.ui, tooltips)

    def load_view(self):
        """Odświeża wszystkie sekcje widoku Live Feed."""
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Live Feed"))
        try:
            self.refresh_event_log()
            self.update_clustering_status()
            
            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", "Live Feed"))
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))


    def refresh_event_log(self):
        """
        Miejsce do pobierania i wyświetlania najnowszych logów z bazy danych.
        """
        # Jeśli lista jest pusta, wyświetla komunikat powitalny
        if self.ui.list_events.count() == 0:
            item = QListWidgetItem("ℹ️ Monitoring system is ready...")
            self.ui.list_events.addItem(item)
        

    def update_clustering_status(self):
        """Miejsce na logikę przyszłej klasteryzacji."""
        self.ui.lbl_cluster_info.setText(
            "Gathering data points for K-Means analysis... \n"
            "Status: [Pending]"
        )
        self.ui.lbl_cluster_info.setStyleSheet("color: #7f8c8d; font-style: italic;")

    def add_log_entry(self, message):
        """Dodaje log i dba o porządek na liście."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"[{timestamp}] {message}")
        
        self.ui.list_events.insertItem(0, item)
        
        # Ogranicza listę do ostatnich 50 wpisów
        if self.ui.list_events.count() > 50:
            self.ui.list_events.takeItem(self.ui.list_events.count() - 1)