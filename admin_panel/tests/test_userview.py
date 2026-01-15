import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# --- KONFIGURACJA ŚCIEŻEK ---
current_path = Path(__file__).resolve()
base_dir = None
for parent in current_path.parents:
    if (parent / 'data').exists() and (parent / 'views').exists():
        base_dir = parent
        break
sys.path.insert(0, str(base_dir or current_path.parent.parent.parent))

from data.database import get_connection
from views.users_view import UsersView
from data.repositories.user_repo import UserRepository

app = QApplication.instance() or QApplication(sys.argv)

class TestUserViewUI(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection()
        self.view = UsersView(self.conn)
        self.table = self.view.ui.table_users
        self.view.load_view()

    def tearDown(self):
        self.view.deleteLater()

    def test_debug_data_flow(self):
        """Diagnostyka: Śledzenie wartości pages_per_day dla oliwier86."""
        target = "oliwier86"
        print(f"\n\n=== ANALIZA PRZEPŁYWU DANYCH DLA: {target} ===")

        # 1. SPRAWDZENIE BAZY (Raw SQL)
        cursor = self.conn.cursor()
        cursor.execute("SELECT pages_per_day, status FROM users WHERE name = ?", (target,))
        db_row = cursor.fetchone()
        db_val = db_row[0] if db_row else "MISSING"
        print(f"[KROK 1] Baza danych (SQL) mówi: {db_val} (status: {db_row[1] if db_row else '?'})")

        # 2. SPRAWDZENIE REPOZYTORIUM (Obiekt Python)
        repo = UserRepository(self.conn)
        users = repo.get_all(period="All Time")
        user_obj = next((u for u in users if u.name == target), None)
        repo_val = user_obj.pages_per_day if user_obj else "MISSING"
        print(f"[KROK 2] Repozytorium (Obiekt) mówi: {repo_val}")

        # 3. SPRAWDZENIE WIDOKU (Tabela UI)
        ui_val = "NOT FOUND"
        for r in range(self.table.rowCount()):
            if self.table.item(r, 1).text() == target:
                ui_val = self.table.item(r, 5).text()
                break
        print(f"[KROK 3] Tabela UI wyświetla: {ui_val}")

        # WNIOSKI:
        if db_val == 0 and repo_val != 0:
            print("\n!!! WNIOSEK: Błąd w 'data/repositories/user_repo.py' lub modelu User.")
        elif repo_val == 0 and ui_val != "0.0":
            print("\n!!! WNIOSEK: Błąd w 'views/users_view.py' (metoda load_view).")
        elif db_val != 0:
            print("\n!!! WNIOSEK: Błąd w GENERATORZE (Baza danych ma błędne wartości).")

    def test_ui_inactive_users_have_zero_pages(self):
        """Standardowy test spójności."""
        errors = []
        for r in range(self.table.rowCount()):
            status = self.table.item(r, 7).text().lower()
            pages = self.table.item(r, 5).text()
            if status == "inactive" and float(pages) != 0.0:
                name = self.table.item(r, 1).text()
                errors.append(f"{name}: {pages}")
        self.assertEqual(len(errors), 0, "Wykryto błędy:\n" + "\n".join(errors))

if __name__ == "__main__":
    unittest.main()