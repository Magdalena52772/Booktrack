import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Konfiguracja ścieżek dostępu do modułów projektu
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

# Inicjalizacja instancji aplikacji dla silnika graficznego PySide6
app = QApplication.instance() or QApplication(sys.argv)

class TestUserViewUI(unittest.TestCase):
    def setUp(self):
        # Inicjalizacja połączenia z bazą danych i komponentu widoku
        self.conn = get_connection()
        self.view = UsersView(self.conn)
        self.table = self.view.ui.table_users
        self.repo = UserRepository(self.conn)
        self.view.load_view()

    def tearDown(self):
        # Zwolnienie zasobów widoku po zakończeniu testu
        self.view.deleteLater()

    def test_01_debug_data_flow(self):
        # Weryfikacja spójności przepływu danych między SQL a warstwą prezentacji
        print("\n\n=== [TEST 01] ANALIZA PRZEPŁYWU DANYCH ===")

        if self.table.rowCount() == 0:
            self.skipTest("Tabela UI jest pusta - brak danych do analizy.")

        target_username = self.table.item(0, 1).text()
        ui_ppd_str = self.table.item(0, 5).text()
        ui_ppd_val = float(ui_ppd_str) if ui_ppd_str else -1.0

        print(f"Target: {target_username} | UI PPD: {ui_ppd_val}")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT u.id, u.pages_per_day,
                   (SELECT COUNT(*) FROM activity WHERE user_id = u.id) as act_count,
                   (SELECT SUM(pages_read) FROM activity WHERE user_id = u.id) as total_pages
            FROM users u WHERE u.username = ?
        """, (target_username,))
        db_row = cursor.fetchone()

        if not db_row:
            self.fail(f"Błąd krytyczny: Użytkownik {target_username} zniknął z bazy!")

        u_id, db_ppd_col, act_count, total_pages = db_row
        total_pages = total_pages or 0

        users = self.repo.get_all(period="all")
        user_obj = next((u for u in users if getattr(u, 'username', getattr(u, 'nickname', None)) == target_username), None)
        repo_ppd = user_obj.pages_per_day if user_obj else None

        print(f"SQL Col: {db_ppd_col} | SQL Activity Sum: {total_pages} | Repo Obj: {repo_ppd}")

        if act_count > 0 and repo_ppd != ui_ppd_val:
            print("❌ Widok nie odświeża danych poprawnie.")
        elif total_pages > 0 and repo_ppd == 0:
            print("❌ Repozytorium ignoruje tabelę activity.")
        else:
            print("✅ Przepływ danych dla tego rekordu jest spójny.")

    def test_02_table_vs_repo_consistency_deep_scan(self):
        # Weryfikacja statystyk PPD z uproszczonym raportowaniem błędów
        test_data = {6: "piotrstempniak520", 500: "mieszkopopielarczyk272"}
        
        print("\n=== [TEST 02] SKAN NICKÓW ===")
        for target_id, nickname in test_data.items():
            self.view.ui.input_search_user.setText(nickname)
            self.view.reset_pagination_and_load()
            
            if self.table.rowCount() == 0:
                continue

            ui_ppd = float(self.table.item(0, 5).text())
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT ROUND(CAST(SUM(pages_read) AS FLOAT) / 
                       NULLIF(COUNT(DISTINCT DATE(timestamp)), 0), 1)
                FROM activity WHERE user_id = ?
            """, (target_id,))
            real_ppd = cursor.fetchone()[0] or 0.0
            
            # print dla istotnych danych
            diff = round(abs(ui_ppd - real_ppd), 1)
            if diff > 0.2:
                print(f"❌ {nickname}: UI({ui_ppd}) vs Real({real_ppd}) | Błąd: +{diff}!")
            else:
                print(f"✅ {nickname}: OK")
            
            with self.subTest(user=nickname):
                self.assertAlmostEqual(ui_ppd, real_ppd, places=1)

    def test_03_inactive_users_zero_check(self):
        # Sprawdzenie czy użytkownicy ze statusem 'inactive' posiadają zerowe wskaźniki aktywności
        errors = []
        for r in range(self.table.rowCount()):
            status = self.table.item(r, 7).text().lower()
            ppd = float(self.table.item(r, 5).text())
            
            if status == "inactive" and ppd != 0.0:
                errors.append(f"{self.table.item(r, 1).text()} ({ppd} PPD)")
        
        self.assertEqual(len(errors), 0, f"Nieaktywni z niezerowym PPD: {errors}")

    def test_04_deep_metrics_analysis(self):
        # Szczegółowa walidacja metryk w widoku rozszerzonym profilu użytkownika
        print("\n=== [TEST 04] ANALIZA PANELU DETALI ===")
        
        target_id, target_row = None, 0
        for r in range(self.table.rowCount()):
            if float(self.table.item(r, 5).text()) > 0:
                target_id = int(self.table.item(r, 0).text())
                target_row = r
                break
        
        if not target_id:
            self.skipTest("Brak aktywnych użytkowników do przetestowania detali.")

        # Emulacja interakcji użytkownika z wierszem tabeli
        self.view.display_user_details(target_row, 0)
        
        profile = self.repo.get_detailed_user_profile(target_id)
        active_ppd = profile.get('active_ppd', 0)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT SUM(pages_read), COUNT(DISTINCT DATE(timestamp))
            FROM activity WHERE user_id = ?
        """, (target_id,))
        total_p, active_d = cursor.fetchone()
        expected_ppd = round(total_p / active_d, 1) if active_d > 0 else 0.0

        print(f"ID {target_id}: Expected {expected_ppd} | Got {active_ppd}")
        
        # Weryfikacja poprawności parsowania danych do formatu HTML w etykiecie informacyjnej
        detail_text = self.view.ui.lbl_info.text()
        self.assertIn(str(expected_ppd), detail_text, "Etykieta HTML w UI pokazuje błędne dane!")
        self.assertAlmostEqual(active_ppd, expected_ppd, places=1)

if __name__ == "__main__":
    # Uruchomienie zestawu testów jednostkowych i integracyjnych
    unittest.main()