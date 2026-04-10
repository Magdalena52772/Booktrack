import sys
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

# --- USTAWIANIE ŚCIEŻEK ---
current_path = Path(__file__).resolve()
base_dir = next((p for p in current_path.parents if (p / 'data').exists()), current_path.parent.parent)
sys.path.insert(0, str(base_dir))

from data.database import get_connection
from views.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestActivityPerformance(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection()
        self.window = MainWindow(self.conn)
        # Przełącza na Activity
        self.window.ui.btn_activity.click()
        QApplication.processEvents()
        # Pobiera instancję widoku (ActivityView)
        self.view = self.window.view_config[self.window.ui.btn_activity]["instance"]

    def tearDown(self):
        self.window.close()

    def test_filter_latency(self):
        """Mierzy czas reakcji na zmianę filtra czasowego (SQL + Render Wykresu)."""
        print("\n" + "="*75)
        print("          AUDYT WYDAJNOŚCI MODUŁU ANALITYCZNEGO (ACTIVITY)")
        print("="*75)
        print(f"{'Filtr Czasowy':<20} | {'Czas [s]':<12} | {'Werdykt'}")
        print("-" * 75)

        # Pobiera opcje z ComboBoxa
        filters = [self.view.ui.cb_time_filter.itemText(i) 
                   for i in range(self.view.ui.cb_time_filter.count())]

        for f_text in filters:
            start_time = time.perf_counter()
            
            # Zmiana filtra w UI
            self.view.ui.cb_time_filter.setCurrentText(f_text)
            
            # Wymusza przeliczenie wszystkiego i narysowanie wykresu
            QApplication.processEvents()
            
            duration = time.perf_counter() - start_time
            
            # Werdykt (na win32)
            if duration < 0.3:
                verdict = "WYBITNY"
            elif duration < 0.8:
                verdict = "AKCEPTOWALNY"
            else:
                verdict = "OPÓŹNIENIE (LAG)"

            print(f"{f_text:<20} | {duration:10.4f}s | {verdict}")

        print("-" * 75)
        print("Wniosek: Czas obejmuje zapytania SQL, KPI oraz renderowanie HTML.")
        print("="*75)

if __name__ == "__main__":
    unittest.main()