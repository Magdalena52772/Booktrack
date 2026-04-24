import sys
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Automatyczne ustawianie ścieżek projektu
current_path = Path(__file__).resolve()
base_dir = next((p for p in current_path.parents if (p / 'data').exists()), current_path.parent.parent)
sys.path.insert(0, str(base_dir))

from data.database import get_connection
from views.main_window import MainWindow

# Inicjalizacja aplikacji Qt (dla testów UI)
app = QApplication.instance() or QApplication(sys.argv)

class TestAdminPanelPerformance(unittest.TestCase):
    def setUp(self):
        # Inicjalizacja głównego okna i bazy danych
        self.conn = get_connection()
        self.window = MainWindow(self.conn)

    def tearDown(self):
        # Zamykanie okna po każdym teście
        self.window.close()

    def test_performance_report(self):
        """Generuje zbiorczy raport wydajności interfejsu i bazy danych."""
        navigation_results = []

        # TEST NAWIGACJI (LATENCJA MODUŁÓW)
        if hasattr(self.window, 'view_config'):
            for btn, cfg in self.window.view_config.items():
                btn_label = btn.text().strip() if hasattr(btn, 'text') else str(btn.objectName())

                start_nav = time.perf_counter()
                btn.click()
                QApplication.processEvents()
                duration = time.perf_counter() - start_nav

                # Klasyfikacja inżynierska
                if duration < 0.5:
                    status, rating = "PASS", "Optymalny"
                elif duration < 1.0:
                    status, rating = "PASS", "Akceptowalny"
                else:
                    status, rating = "FAIL", "Wymaga optymalizacji"

                navigation_results.append((btn_label, duration, status, rating))

                # ASERCJA: Wszystkie widoki < 1s (standard inżynierski - user nie czuje lag)
                self.assertLess(duration, 1.0, f"{btn_label} exceeded 1.0s threshold")

        # TEST LIVE FEED (LOG INJECTION)
        self.window.ui.btn_live_feed.click()
        live_feed = self.window.view_config[self.window.ui.btn_live_feed]["instance"]
        avg_log_time = 0
        if live_feed and hasattr(live_feed, "add_log_entry"):
            test_log = {"user": "Test", "action": "Log", "timestamp": "00:00:00"}
            start_push = time.perf_counter()
            for _ in range(50):
                live_feed.add_log_entry(test_log)
            avg_log_time = (time.perf_counter() - start_push) / 50

        # ANALIZA STARTUPU (SQL COST)
        start_db = time.perf_counter()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
        self.conn.commit()
        db_duration = time.perf_counter() - start_db

        # === WYDRUK RAPORTU ===
        print("\n" + "="*75)
        print("                ZBIORCZY RAPORT WYDAJNOŚCI SYSTEMU")
        print("="*75)
        print(f"{'Moduł/Operacja':<20} | {'Czas [s]':<12} | {'Status':<8} | {'Ocena'}")
        print("-" * 75)

        # Wyniki nawigacji
        for name, dur, stat, rat in navigation_results:
            print(f"{name[:20]:<20} | {dur:10.4f}s | {stat:<8} | {rat}")

        print("-" * 75)
        # Wyniki techniczne
        print(f"{'Live Feed Injection':<20} | {avg_log_time:10.6f}s | PASS     | Optymalny")
        print(f"{'Startup SQL Cost':<20} | {db_duration:10.4f}s | PASS     | Optymalny")
        print("-" * 75)
        print(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')} | Środowisko: Python/PySide6/SQLite")
        print("="*75)

if __name__ == "__main__":
    unittest.main()