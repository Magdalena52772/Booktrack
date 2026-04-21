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
from data.repositories.activity_repo import ActivityRepository
from views.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestActivityPerformance(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection()
        self.repo = ActivityRepository(self.conn)
        self.window = MainWindow(self.conn)
        # Przełącza na Activity
        self.window.ui.btn_activity.click()
        QApplication.processEvents()
        # Pobiera instancję widoku (ActivityView)
        self.view = self.window.view_config[self.window.ui.btn_activity]["instance"]

    def tearDown(self):
        self.window.close()

    def test_filter_latency_detailed(self):
        """
        Audyt wydajności ACTIVITY VIEW - szczegółowe pomiary:
        - KPI Time: zapytania SQL dla wskaźników
        - Trend Time: zapytania SQL dla wykresu
        - Total Time: cały czas ładowania filtra (SQL + render)
        """
        print("\n" + "="*95)
        print("          AUDYT WYDAJNOŚCI MODUŁU ANALITYCZNEGO (ACTIVITY)")
        print("="*95)
        print(f"{'Filtr':<10} | {'KPI [s]':<15} | {'Trend [s]':<15} | {'Total [s]':<12} | {'Verdict'}")
        print("-" * 100)

        # Pobiera opcje z ComboBoxa
        filters = [self.view.ui.cb_time_filter.itemText(i)
                   for i in range(self.view.ui.cb_time_filter.count())]

        for f_text in filters:
            # Mierzy KPI queries
            t_kpi_start = time.perf_counter()
            total_pages, real_active_days, _ = self.repo.get_activity_kpi(f_text)
            unique_readers = self.repo.get_unique_active_users(f_text)
            kpi_time = time.perf_counter() - t_kpi_start

            # Mierzy Trend queries
            t_trend_start = time.perf_counter()
            trend_data = self.repo.get_activity_trend(f_text)
            trend_time = time.perf_counter() - t_trend_start

            # Mierzy całkowity czas ładowania filtra (w UI)
            t_total_start = time.perf_counter()
            self.view.ui.cb_time_filter.setCurrentText(f_text)
            QApplication.processEvents()
            total_time = time.perf_counter() - t_total_start

            # Werdykt dla TOTAL
            if total_time < 0.3:
                total_verdict = "WYBITNY"
            elif total_time < 1.0:
                total_verdict = "AKCEPTOWALNY"
            else:
                total_verdict = "OPÓŹNIENIE (LAG)"

            # Werdykt dla KPI
            if kpi_time < 0.2:
                kpi_verdict = "SUPER"
            elif kpi_time < 0.5:
                kpi_verdict = "OK"
            elif kpi_time < 1.0:
                kpi_verdict = "SLOW"
            else:
                kpi_verdict = "VERY SLOW"

            # Werdykt dla TREND
            if trend_time < 0.1:
                trend_verdict = "SUPER"
            elif trend_time < 0.2:
                trend_verdict = "OK"
            elif trend_time < 0.5:
                trend_verdict = "SLOW"
            else:
                trend_verdict = "VERY SLOW"

            print(f"{f_text:<10} | {kpi_time:8.4f}s ({kpi_verdict:<10}) | {trend_time:8.4f}s ({trend_verdict:<10}) | {total_time:8.4f}s | {total_verdict}")

            # ASERCJA: Całkowity czas < 1.2s (łączy SQL + render matplotlib)
            self.assertLess(total_time, 1.2,
                f"Filter '{f_text}' exceeded 1.2s threshold (Total: {total_time:.3f}s, KPI: {kpi_time:.3f}s, Trend: {trend_time:.3f}s)")

        print("-" * 100)
        print("NORMY WYDAJNOŚCI:")
        print("  KPI Time:   < 0.2s = SUPER,  < 0.5s = OK,     < 1.0s = SLOW,      >= 1.0s = VERY SLOW")
        print("  Trend Time: < 0.1s = SUPER,  < 0.2s = OK,     < 0.5s = SLOW,      >= 0.5s = VERY SLOW")
        print("  TOTAL:      < 0.3s = WYBITNY, < 1.0s = AKCEPTOWALNY, >= 1.0s = OPÓŹNIENIE (LAG)")
        print("="*100)

if __name__ == "__main__":
    unittest.main()
