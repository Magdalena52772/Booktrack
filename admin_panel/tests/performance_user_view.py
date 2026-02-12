import sys
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ustawianie ścieżek dostępu do modułów projektu
current_path = Path(__file__).resolve()
base_dir = None
for parent in current_path.parents:
    if (parent / 'data').exists() and (parent / 'views').exists():
        base_dir = parent
        break
sys.path.insert(0, str(base_dir or current_path.parent.parent.parent))

from data.database import get_connection
from views.users_view import UsersView

app = QApplication.instance() or QApplication(sys.argv)

class TestUserViewPerformance(unittest.TestCase):
    def setUp(self):
        """Inicjalizacja połączenia z bazą przed testami."""
        self.conn = get_connection()

    def test_loading_speed_breakdown(self):
        """Analiza porównawcza czasu zapytania SQL oraz renderowania tabeli."""
        # Tworzenie widoku na potrzeby testu cząstkowego
        view = UsersView(self.conn)
        table = view.ui.table_users
        
        print(f"\n\n=== RAPORT WYDAJNOŚCI OPERACJI USERS ===")
        
        # Etap 1: Pomiar czasu w warstwie danych
        start_db = time.perf_counter()
        users = view.repo.get_all(period="all", limit=50)
        end_db = time.perf_counter()
        db_time = end_db - start_db
        
        # Etap 2: Pomiar czasu w warstwie UI
        table.setSortingEnabled(False)
        table.blockSignals(True)
        
        start_ui = time.perf_counter()
        view.load_view() 
        end_ui = time.perf_counter()
        
        ui_time = end_ui - start_ui
        
        print(f"1. Czas Bazy Danych (SQL):        {db_time:.4f}s")
        print(f"2. Czas Renderowania UI (Tabela): {ui_time:.4f}s")
        print(f"---------------------------------------------")
        
        view.deleteLater()
        self.assertLess(db_time + ui_time, 1.0)

    def test_view_initialization_cost(self):
        """Pomiar całkowitego kosztu utworzenia instancji widoku (Cold Start)."""
        print(f"\n\n=== POMIAR INICJALIZACJI (COLD START) ===")
        
        # Pomiar czasu tworzenia obiektów i ładowania zasobów
        start_init = time.perf_counter()
        view = UsersView(self.conn)
        mid_init = time.perf_counter()
        
        # Pomiar pierwszego wypełnienia danymi
        view.load_view()
        end_init = time.perf_counter()
        
        init_ui_cost = mid_init - start_init
        first_load_cost = end_init - mid_init
        total = init_ui_cost + first_load_cost
        
        print(f"Konstrukcja obiektów UI: {init_ui_cost:.4f}s")
        print(f"Pierwsze wypełnienie:    {first_load_cost:.4f}s")
        print(f"ŁĄCZNY KOSZT STARTU:     {total:.4f}s")
        
        if total > 1.0:
            print("\n[!] UWAGA: Start widoku trwa zbyt długo. Sprawdź konstruktor __init__.")

        view.deleteLater()
        self.assertLess(total, 2.0, "Widok startuje ekstremalnie wolno.")

if __name__ == "__main__":
    unittest.main()