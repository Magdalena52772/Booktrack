from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QListWidgetItem
from datetime import datetime

from data.utils.status_manager import StatusMsg
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips


class LiveFeedView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()

        self.conn = conn

        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/LiveFeedView.ui")

        if not self.ui:
            print("Błąd ładowania UI LiveFeed!")
            return

        # Konfiguracja podpowiedzi
        self.setup_tooltips()

        # Sygnały
        self.ui.btn_refresh_live.clicked.connect(self.load_view)

        # Inicjalizacja danych
        self.load_view()

    def setup_tooltips(self):
        """Podpowiedzi dla sekcji Live Feed."""
        tooltips = {
            "list_events": "Real-time log of recent database changes and user actions.",
            "btn_refresh_live": "Manually refresh to see the latest events and daily metrics.",
        }
        apply_tooltips(self.ui, tooltips)

    def load_view(self):
        """Odświeża logi oraz wskaźniki KPI w widoku Live Feed."""
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Live Feed"))
        try:
            self.refresh_event_log()
            self.update_daily_metrics()

            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", "Live Feed"))
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))

    def refresh_event_log(self):
        """Pobiera i wyświetla ostatnie logi aktywności z bazy danych."""
        from data.repositories.activity_repo import ActivityRepository

        # Czyści listę
        self.ui.list_events.clear()

        # Pobiera ostatnie 50 logów
        activity_repo = ActivityRepository(self.conn)
        logs = activity_repo.get_recent_activity_logs(limit=50)

        if logs:
            for time_str, message in logs:
                self.add_log_entry(message, timestamp=time_str)
        else:
            item = QListWidgetItem(
                "ℹ️ Monitoring system is ready... Waiting for activity logs."
            )
            self.ui.list_events.addItem(item)

    def update_daily_metrics(self):
        """Pobiera i wyświetla dzisiejsze KPI (rozpoczęte i ukończone książki)."""
        try:
            cursor = self.conn.cursor()
            today_str = datetime.now().strftime("%Y-%m-%d")

            # Książki rozpoczęte dzisiaj
            cursor.execute("""
                SELECT COUNT(*) FROM user_books
                WHERE date(start_date) = ?
            """, (today_str,))
            start_date = cursor.fetchone()[0] or 0

            # Książki ukończone dzisiaj
            cursor.execute("""
                SELECT COUNT(*) FROM user_books
                WHERE status = 'finished' AND date(finish_date) = ?
            """, (today_str,))
            finish_date = cursor.fetchone()[0] or 0

            # Aktualizacja etykiet w UI
            if hasattr(self.ui, "lbl_books_started_title"):
                self.ui.lbl_books_started_title.setText(f"📚 Books Started Today: {start_date}")
            if hasattr(self.ui, "lbl_books_finished_title"):
                self.ui.lbl_books_finished_title.setText(f"✅ Books Finished Today: {finish_date}")

        except Exception as e:
            print(f"[METRICS ERROR] Nie udało się pobrać dzisiejszych KPI: {e}")

    def add_log_entry(self, message, timestamp=None):
        """Dodaje wpis logu do listy w widoku Live Feed"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        item = QListWidgetItem(f"[{timestamp}] {message}")
        self.ui.list_events.insertItem(0, item)

        # Ogranicza listę do ostatnich 50 wpisów
        if self.ui.list_events.count() > 50:
            self.ui.list_events.takeItem(self.ui.list_events.count() - 1)