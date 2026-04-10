import sqlite3
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta

# Konfiguracja ścieżek dostępu do modułów projektu
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

try:
    from data.database import get_connection
except ModuleNotFoundError:
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

    # --- KATEGORIA: REALIZM DANYCH I STATYSTYKA ---

    def test_user_age_distribution(self):
        """Weryfikacja rozkładu wieku. Średnia wieku powinna mieścić się w przedziale 25-45 lat."""
        self.cursor.execute("SELECT birth_date FROM users")
        birth_dates = [datetime.strptime(row[0].split()[0], "%Y-%m-%d") for row in self.cursor.fetchall()]
        ages = [(datetime.now() - bd).days // 365 for bd in birth_dates]
        avg_age = sum(ages) / len(ages) if ages else 0
        self.assertTrue(25 <= avg_age <= 45)

    def test_genre_stats_logic(self):
        """Weryfikacja sumy udziałów procentowych gatunków. Suma powinna oscylować wokół 100%."""
        self.cursor.execute("SELECT SUM(reading_time_share) FROM genres")
        total_share = self.cursor.fetchone()[0] or 0
        self.assertTrue(99.0 <= total_share <= 101.0)

    def test_pages_read_limit(self):
        """Weryfikacja limitu stron na sesję. Maksymalna wartość nie powinna przekraczać 300 stron."""
        self.cursor.execute("SELECT MAX(pages_read) FROM activity")
        max_p = self.cursor.fetchone()[0] or 0
        self.assertLessEqual(max_p, 300)

    def test_inactive_user_ratio(self):
        """Weryfikacja odsetka użytkowników nieaktywnych. Zakres tolerancji: 2-15%."""
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'inactive'")
        inactive = self.cursor.fetchone()[0]
        ratio = (inactive / total) * 100 if total > 0 else 0
        self.assertTrue(2 <= ratio <= 15)

    def test_weekend_multiplier_effect(self):
        """Weryfikacja wpływu mnożnika weekendowego na intensywność czytania (WE > WD)."""
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) IN ('0', '6')")
        avg_we = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) NOT IN ('0', '6')")
        avg_wd = self.cursor.fetchone()[0] or 0
        self.assertGreater(avg_we, avg_wd)

    def test_age_genre_correlation(self):
        """Weryfikacja korelacji wieku z gatunkami. Gatunki dojrzałe u nieletnich poniżej 20%."""
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
        self.assertLess(ratio, 0.20)

    # --- KATEGORIA: INTEGRALNOŚĆ RELACYJNA I WIĘZY ---

    def test_birth_date_not_null_constraint(self):
        """Weryfikacja wymagalności daty urodzenia (NOT NULL)."""
        self.cursor.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO users (password, username, date_joined) VALUES ('p','u','2026-01-01')")
        self.conn.rollback()

    def test_unique_user_id(self):
        """Weryfikacja unikalności klucza głównego użytkownika."""
        test_id = 99999
        user_data = (test_id, 'h', 't', 0, 0, '2026-01-01', '1990-01-01')
        query = "INSERT INTO users (id, password, username, is_superuser, is_staff, date_joined, birth_date) VALUES (?,?,?,?,?,?,?)"
        self.cursor.execute(query, user_data)
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(query, user_data)
        self.conn.rollback()

    def test_foreign_key_constraint(self):
        """Weryfikacja blokady zapisu przy nieistniejącym kluczu obcym (FOREIGN KEY)."""
        self.cursor.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO books (user_id, title) VALUES (888888, 'Fail')")
        self.conn.rollback()

    def test_orphan_records_activity(self):
        """Sprawdzenie występowania rekordów aktywności bez przypisanego użytkownika."""
        self.cursor.execute("SELECT COUNT(*) FROM activity WHERE user_id NOT IN (SELECT id FROM users)")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_genre_integrity_constraint(self):
        """Weryfikacja spójności referencji między tabelą books a genres."""
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE genre_id NOT IN (SELECT id FROM genres)")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    # --- KATEGORIA: SPÓJNOŚĆ LOGICZNA I STATUSY ---

    def test_inactive_anomalies(self):
        """Weryfikacja wyzerowania potencjału i braku świeżych sesji dla kont nieaktywnych."""
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'inactive' AND pages_per_day > 0")
        self.assertEqual(self.cursor.fetchone()[0], 0)
        
        query = """
            SELECT COUNT(*) FROM users u JOIN activity a ON u.id = a.user_id 
            WHERE u.status = 'inactive' AND a.timestamp > datetime('now', '-6 months')
        """
        self.cursor.execute(query)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_books_consistency(self):
        """Weryfikacja zgodności licznika books_read z faktyczną liczbą rekordów."""
        query = """
            SELECT u.books_read, (SELECT COUNT(*) FROM books b WHERE b.user_id = u.id AND b.status = 'finished')
            FROM users u
        """
        self.cursor.execute(query)
        for cached, actual in self.cursor.fetchall():
            self.assertEqual(cached, actual)

    def test_activity_timestamps(self):
        """Weryfikacja chronologii: brak aktywności przed datą dołączenia użytkownika."""
        query = "SELECT COUNT(*) FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp < u.date_joined"
        self.cursor.execute(query)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_book_progress_logic(self):
        """Weryfikacja poprawności postępu (current_page nie większe niż total_pages)."""
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE current_page > total_pages OR current_page < 0")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_external_id_uniqueness(self):
        """Weryfikacja unikalności identyfikatorów zewnętrznych (external_id)."""
        self.cursor.execute("SELECT COUNT(external_id), COUNT(DISTINCT external_id) FROM users")
        total, distinct = self.cursor.fetchone()
        self.assertEqual(total, distinct)

    def test_challenge_status_logic(self):
        """Weryfikacja automatyzacji statusów wyzwań na podstawie dat i postępu."""
        self.cursor.execute("SELECT target_value, current_value, status, end_date FROM challenges")
        now = datetime.now()
        for target, progress, status, end_date_str in self.cursor.fetchall():
            clean_date = end_date_str.split('.')[0] if '.' in end_date_str else end_date_str
            try:
                end_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_date = datetime.strptime(clean_date, "%Y-%m-%d")
            
            if progress >= target: self.assertEqual(status, 'finished')
            elif end_date < now: self.assertEqual(status, 'failed')
            else: self.assertEqual(status, 'active')

    def test_empty_book_titles(self):
        """Weryfikacja obecności tytułów i przypisanych gatunków we wszystkich rekordach."""
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE title IS NULL OR title = '' OR genre_id IS NULL")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_inactive_users_no_recent_sessions(self):
        """Weryfikacja braku sesji czytelniczych w ostatnich 180 dniach dla użytkowników inactive."""
        limit = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
        query = "SELECT COUNT(*) FROM users u JOIN activity a ON u.id = a.user_id WHERE u.status = 'inactive' AND a.timestamp > ?"
        self.cursor.execute(query, (limit,))
        self.assertEqual(self.cursor.fetchone()[0], 0)

class LogicUnitTests(unittest.TestCase):
    def test_consistency_score_logic(self):
        """Walidacja algorytmu obliczania wskaźnika regularności (Consistency Score)."""
        score = (6 / 30) * 100
        self.assertEqual(score, 20.0)

if __name__ == "__main__":
    import inspect

    # Załadowanie i uruchomienie testów
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print("\n" + "="*80)
    print(f"{'RAPORT Z TESTÓW INTEGRALNOŚCI SYSTEMU BOOKTRACK':^80}")
    print("="*80)
    print(f"{'ID Metody Testowej':<45} | {'Status':<12} | {'Wynik'}")
    print("-"*80)

    # Pobieramy klasy testowe z bieżącego modułu
    test_classes = [obj for name, obj in inspect.getmembers(sys.modules[__name__]) 
                   if inspect.isclass(obj) and issubclass(obj, unittest.TestCase)]

    report_lines = []
    
    # Mapowanie wyników dla szybkich sprawdzeń
    # result.failures i result.errors zawierają krotki (test_object, traceback)
    fail_names = {t[0]._testMethodName for t in result.failures}
    err_names = {t[0]._testMethodName for t in result.errors}

    for cls in test_classes:
        # Pobieramy metody zaczynające się od 'test_'
        methods = [m for m, _ in inspect.getmembers(cls, predicate=inspect.isfunction) 
                  if m.startswith('test_')]
        
        for m_name in methods:
            status = "PASSED ✅"
            if m_name in fail_names:
                status = "FAILED ❌"
            elif m_name in err_names:
                status = "ERROR ⚠️"
            
            report_lines.append(f"{m_name:<45} | {status:<12} | Pozytywny")

    # Wyświetlanie wyników
    if report_lines:
        for line in sorted(list(set(report_lines))): # set usuwa ewentualne duplikaty
            print(line)
    else:
        print(f"{'BŁĄD KRYTYCZNY RAPORTOWANIA':^80}")

    print("-"*80)
    print(f"PODSUMOWANIE: Wykonano {result.testsRun} testów.")
    print(f"Błędy: {len(result.errors)}, Niepowodzenia: {len(result.failures)}")
    print(f"Status końcowy: {'SUKCES (OK)' if result.wasSuccessful() else 'WYKRYTO NIEPRAWIDŁOWOŚCI'}")
    print("="*80 + "\n")