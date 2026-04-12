import sys
import time
import os
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

# --- KONFIGURACJA ŚCIEŻEK ---
current_path = Path(__file__).resolve()
base_dir = next((p for p in current_path.parents if (p / 'data').exists()), current_path.parent.parent)
sys.path.insert(0, str(base_dir))

from data.database import get_connection, initialize_database
from data.services.maintenance_service import update_genre_stats
from views.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestUISmoothnessEverywhere(unittest.TestCase):
    def setUp(self):
        initialize_database()
        self.conn = get_connection()
        self.window = MainWindow(self.conn)
        self.window.show()

    def tearDown(self):
        self.window.close()

    def test_smoothness_per_view(self):
        """Testuje płynność UI i generuje raport wydajności dla wszystkich modułów systemu."""
        results = []
        
        # Zapamiętuje oryginalne wyjście konsoli
        original_stdout = sys.stdout

        for btn, cfg in self.window.view_config.items():
            btn_label = btn.text().strip() if hasattr(btn, 'text') else str(btn.objectName())
            btn.click()
            QApplication.processEvents()
            
            delays = []
            start_view_test = time.perf_counter()
            
            while time.perf_counter() - start_view_test < 2:
                frame_start = time.perf_counter()
                
                # WYCISZANIE: Przekierowuje printy do os.devnull
                with open(os.devnull, 'w') as f:
                    sys.stdout = f
                    update_genre_stats(self.conn)
                    sys.stdout = original_stdout # Przywraca, żeby mierzyć dalej
                
                app.processEvents()
                
                frame_time = (time.perf_counter() - frame_start) * 1000
                delays.append(frame_time)

            max_d = max(delays) if delays else 0
            avg_d = sum(delays) / len(delays) if delays else 0
            
            if max_d < 32:
                rating = "Płynnie"
            elif max_d < 150:
                rating = "Dostrzegalny lag"
            else:
                rating = "KRYTYCZNE PRZYCIĘCIE"

            results.append((btn_label, max_d, avg_d, rating))

        # RAPORT
        print("\n" + "="*75)
        print("           RAPORT PŁYNNOŚCI INTERFEJSU (STRESS TEST SYSTEMU)")
        print("="*75)
        print(f"{'Moduł Systemu':<18} | {'Max Lag [ms]':<15} | {'Śr. Lag [ms]':<12} | {'Ocena'}")
        print("-" * 75)
        
        for name, m, a, r in results:
            print(f"{name[:18]:<18} | {m:10.2f} ms | {a:9.2f} ms | {r}")

        print("-" * 75)
        print(f"Środowisko: {sys.platform} | Obciążenie: Batch SQL Update")
        print("="*75)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUISmoothnessEverywhere)
    unittest.TextTestRunner(verbosity=0).run(suite)