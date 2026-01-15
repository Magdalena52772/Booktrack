import sys
import unittest
import csv
from pathlib import Path
from datetime import datetime

# Konfiguracja ścieżek dostępu do modułów projektu
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

try:
    from data.database import get_connection
except ModuleNotFoundError:
    print(f"BŁĄD: Nie znaleziono modułu 'data'. Szukano w: {BASE_DIR}")
    sys.exit(1)

class TestGeneratorLogic(unittest.TestCase):
    """
    Zestaw testów walidacyjnych dla generatora danych oraz integralności bazy danych.
    Weryfikacja logiki biznesowej, rozkładów statystycznych i więzów spójności.
    """

    @classmethod
    def setUpClass(cls):
        """Inicjalizacja połączenia z bazą danych na potrzeby sesji testowej."""
        cls.conn = get_connection()
        cls.cursor = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        """Zamykanie połączenia z bazą danych po zakończeniu wszystkich testów."""
        cls.conn.close()

    # --- TESTY STATYSTYCZNE I LOGIKI BIZNESOWEJ ---

    def test_user_age_distribution(self):
        """Weryfikacja rozkładu wieku. Średnia wieku powinna mieścić się w przedziale 25-45 lat."""
        self.cursor.execute("SELECT birth_date FROM users")
        birth_dates = [datetime.strptime(row[0].split()[0], "%Y-%m-%d") for row in self.cursor.fetchall()]
        ages = [(datetime.now() - bd).days // 365 for bd in birth_dates]
        avg_age = sum(ages) / len(ages) if ages else 0
        print(f"[SUCCESS] Age distribution verified. Average: {avg_age:.2f} years")
        self.assertTrue(25 <= avg_age <= 45)

    def test_genre_stats_logic(self):
        """Weryfikacja sumy udziałów procentowych gatunków. Suma powinna oscylować wokół 100%."""
        self.cursor.execute("SELECT SUM(reading_time_share) FROM genres")
        total_share = self.cursor.fetchone()[0] or 0
        print(f"[SUCCESS] Genre stats consistent. Total share: {total_share:.2f}%")
        self.assertTrue(99.0 <= total_share <= 101.0)

    def test_pages_read_limit(self):
        """Weryfikacja limitu stron na sesję. Żaden wpis w activity nie powinien przekraczać 50 stron."""
        self.cursor.execute("SELECT MAX(pages_read) FROM activity")
        max_p = self.cursor.fetchone()[0] or 0
        print(f"[SUCCESS] Session limits maintained. Maximum: {max_p} pages")
        self.assertLessEqual(max_p, 50)

    def test_inactive_user_ratio(self):
        """Weryfikacja odsetka użytkowników nieaktywnych. Powinien mieścić się w przedziale 2-15%."""
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'inactive'")
        inactive = self.cursor.fetchone()[0]
        ratio = (inactive / total) * 100 if total > 0 else 0
        print(f"[SUCCESS] Status structure verified. Inactive: {ratio:.2f}%")
        self.assertTrue(2 <= ratio <= 15)

    def test_weekend_multiplier_effect(self):
        """Weryfikacja wpływu mnożnika weekendowego na intensywność czytania."""
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) IN ('0', '6')")
        avg_we = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) NOT IN ('0', '6')")
        avg_wd = self.cursor.fetchone()[0] or 0
        print(f"[SUCCESS] Weekend weights active. WE: {avg_we:.2f} vs WD: {avg_wd:.2f}")
        self.assertGreater(avg_we, avg_wd)

    def test_age_genre_correlation(self):
        """Weryfikacja korelacji wieku z gatunkami. Gatunki dojrzałe u osób poniżej 18 lat powinny być rzadkością."""
        query = """
            SELECT g.name FROM users u 
            JOIN books b ON u.id = b.user_id 
            JOIN genres g ON b.genre_id = g.id 
            WHERE (strftime('%Y', 'now') - strftime('%Y', u.birth_date)) < 18
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if not rows: return
        anomalies = [r[0] for r in rows if r[0] in ["Biography", "Crime", "Historical fiction"]]
        ratio = len(anomalies) / len(rows)
        print(f"[SUCCESS] Age/Genre correlation verified. Anomaly ratio: {ratio:.2f}")
        self.assertLess(ratio, 0.20)

    # --- TESTY INTEGRALNOŚCI I SPÓJNOŚCI DANYCH ---

    def test_inactive_anomalies(self):
        """Sprawdzenie, czy użytkownicy inactive mają wyzerowane tempo oraz brak świeżej aktywności."""
        self.cursor.execute("SELECT name FROM users WHERE status = 'inactive' AND pages_per_day > 0")
        bad_pages = self.cursor.fetchall()
        
        query = """
            SELECT u.name FROM users u 
            JOIN activity a ON u.id = a.user_id 
            WHERE u.status = 'inactive' 
            GROUP BY u.name 
            HAVING MAX(a.timestamp) > datetime('now', '-6 months')
        """
        self.cursor.execute(query)
        bad_activity = self.cursor.fetchall()

        self.assertEqual(len(bad_pages), 0, "Users with status 'inactive' must have pages_per_day = 0")
        self.assertEqual(len(bad_activity), 0, "Users with status 'inactive' cannot have activity in last 6 months")

    def test_books_consistency(self):
        """Weryfikacja spójności liczników. Pole books_read musi zgadzać się z liczbą rekordów w tabeli books."""
        query = """
            SELECT u.books_read, COUNT(b.id) 
            FROM users u 
            LEFT JOIN books b ON u.id = b.user_id AND b.status = 'finished' 
            GROUP BY u.id
        """
        self.cursor.execute(query)
        for cached, actual in self.cursor.fetchall():
            self.assertEqual(cached, actual)

    def test_activity_timestamps(self):
        """Weryfikacja chronologii. Data aktywności nie może być wcześniejsza niż data rejestracji użytkownika."""
        query = "SELECT u.name FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp < u.register_date"
        self.cursor.execute(query)
        self.assertEqual(len(self.cursor.fetchall()), 0)

    def test_book_progress_logic(self):
        """Sprawdzenie poprawności postępu książki. current_page nie może przekraczać total_pages."""
        self.cursor.execute("SELECT title FROM books WHERE current_page > total_pages OR current_page < 0")
        self.assertEqual(len(self.cursor.fetchall()), 0)

    def test_external_id_uniqueness(self):
        """Weryfikacja unikalności identyfikatorów zewnętrznych (external_id)."""
        self.cursor.execute("SELECT COUNT(external_id), COUNT(DISTINCT external_id) FROM users")
        total, distinct = self.cursor.fetchone()
        self.assertEqual(total, distinct)

    def test_challenge_status_logic(self):
        """Weryfikacja automatyki statusów wyzwań na podstawie dat i postępu."""
        self.cursor.execute("SELECT target_books, progress_books, status, end_date FROM challenges")
        now = datetime.now()
        for target, progress, status, end_date_str in self.cursor.fetchall():
            clean_date = end_date_str.split('.')[0] if '.' in end_date_str else end_date_str
            end_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            if progress >= target: 
                self.assertEqual(status, 'finished')
            elif end_date < now: 
                self.assertEqual(status, 'failed')
            else: 
                self.assertEqual(status, 'active')

    def test_orphan_records_activity(self):
        """Sprawdzenie czy istnieją rekordy aktywności nieprzypisane do żadnego użytkownika."""
        self.cursor.execute("SELECT COUNT(*) FROM activity WHERE user_id NOT IN (SELECT id FROM users)")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 0)

    def test_empty_book_titles(self):
        """Weryfikacja czy wszystkie wygenerowane książki posiadają tytuły i przypisane gatunki."""
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE title IS NULL OR title = '' OR genre_id IS NULL")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 0)

    def test_registration_date_range(self):
        """Weryfikacja czy daty rejestracji użytkowników nie wykraczają poza dopuszczalny zakres (max 2 lata wstecz)."""
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE register_date < datetime('now', '-2 years') OR register_date > datetime('now')")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 0)

    def test_genre_integrity_constraint(self):
        """Weryfikacja czy gatunki w tabeli books odpowiadają istniejącym rekordom w tabeli genres."""
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE genre_id NOT IN (SELECT id FROM genres)")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 0)

if __name__ == "__main__":
    unittest.main()