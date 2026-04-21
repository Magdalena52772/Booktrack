import sys
import time
import sqlite3
import unittest
from pathlib import Path

# dynamiczne wyznaczanie sciezki bezwzglednej pliku wykonywalnego
current_file = Path(__file__).resolve()
root_path = None

# iteracyjne przeszukiwanie katalogów nadrzednych w celu lokalizacji folderu data
for parent in current_file.parents:
    if (parent / "data" / "config" /"__init__.py").exists():
        root_path = parent
        break

# aktualizacja zmiennej srodowiskowej sys.path dla poprawnego importu modulów
if root_path:
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))
else:
    # fallback w przypadku niestandardowej struktury katalogów
    root_path = current_file.parent.parent.parent.parent
    sys.path.insert(0, str(root_path))

# bezpieczna próba ladowania konfiguracji sciezki bazy danych
try:
    from data.config import DB_PATH
except ImportError:
    print("BŁŁD: Brak dostepu do konfiguracji projektu.")
    sys.exit(1)

class EngineeringPerformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # sprawdzenie integralnosci srodowiska przed inicjalizacja klasy testowej
        if not DB_PATH.exists():
            sys.exit(1)
        
        # formatowanie naglówka raportu wydajnosciowego dla dokumentacji
        print("\n" + "="*75)
        print(f"PROTOKÓŁ POMIARU WYDAJNOSCI OPERACJI BAZODANOWYCH")
        print("="*75)
        print(f"Baza danych:     {DB_PATH.name}")
        print(f"Sciezka pelna:   {DB_PATH}")
        print(f"Rozmiar zbioru:  {DB_PATH.stat().st_size / 1024:.2f} KB")
        print("-" * 75)
        print(f"{'ZDEFINIOWANY SCENARIUSZ TESTOWY':<45} | {'CZAS':<10} | {'STATUS'}")
        print("-" * 75)

    def setUp(self):
        # otwieranie polaczenia w trybie tylko do odczytu dla bezpieczenstwa danych
        db_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
        self.conn = sqlite3.connect(db_uri, uri=True)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        # zwalnianie zasobów i zamykanie deskryptora pliku bazy
        self.conn.close()

    def _print_formatted_result(self, test_name, elapsed, threshold):
        # weryfikacja czy uzyskany czas miesci sie w zalozonym rezinie czasowym
        status = "ZGODNY" if elapsed < threshold else "PRZEKROCZONY"
        print(f"{test_name:<45} | {elapsed:>8.4f}s | {status}")

    def test_view_users_loading_n_plus_one(self):
        # analiza narzutu wydajnosciowego przy sekwencyjnym pobieraniu danych zaleznych
        start_time = time.perf_counter()
        
        # pobranie partii identyfikatorów uzytkowników
        self.cursor.execute("SELECT id FROM users LIMIT 100")
        users = self.cursor.fetchall()
        
        # symulacja powszechnego bledu projektowego n plus jeden
        for user in users: 
            self.cursor.execute("SELECT COUNT(*) FROM books WHERE user_id = ?", (user[0],))
            _ = self.cursor.fetchone()

        total_duration = time.perf_counter() - start_time
        self._print_formatted_result("Lista uzytkowników (Symulacja N+1)", total_duration, 1.0)
        self.assertLess(total_duration, 1.0)

    def test_view_activity_year_stress(self):
        # test obciazeniowy dla operacji agregacji na duzym zbiorze danych czasowych
        start_time = time.perf_counter()
        
        # zapytanie wykorzystujace funkcje agregujace i grupowanie po dacie
        query = """
            SELECT date(timestamp), SUM(pages_read) 
            FROM activity 
            WHERE timestamp >= date('now', '-1 year') 
            GROUP BY date(timestamp)
        """
        self.cursor.execute(query)
        result_set = self.cursor.fetchall()
        
        total_duration = time.perf_counter() - start_time
        self._print_formatted_result(f"Agregacja roczna ({len(result_set)} rekordów)", total_duration, 1.0)
        self.assertLess(total_duration, 1.0)

    def test_genres_share_heavy_join(self):
        # weryfikacja szybkosci przetwarzania zlaczen lewostronnych miedzy tabelami
        start_time = time.perf_counter()
        
        # zliczanie powiazanych rekordów przy uzyciu relacji kluczy obcych
        query = """
            SELECT g.name, COUNT(b.id) 
            FROM genres g 
            LEFT JOIN books b ON g.id = b.genre_id 
            GROUP BY g.id
        """
        self.cursor.execute(query)
        _ = self.cursor.fetchall()
        
        total_duration = time.perf_counter() - start_time
        self._print_formatted_result("Statystyki gatunków (Relacja JOIN)", total_duration, 1.0)
        self.assertLess(total_duration, 1.0)

    def test_view_user_details_sequential_io(self):
        # pomiar latencji przy wielokrotnym odczycie danych dla pojedynczego obiektu
        self.cursor.execute("SELECT id FROM users LIMIT 1")
        row = self.cursor.fetchone()
        if not row:
            self.skipTest("Brak danych wejsciowych w tabeli users")
        
        user_target_id = row[0]
        start_time = time.perf_counter()
        
        # pobieranie danych rozproszonych w strukturze bazy dla jednego profilu
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_target_id,))
        self.cursor.execute("SELECT * FROM books WHERE user_id = ?", (user_target_id,))
        self.cursor.execute("SELECT SUM(pages_read) FROM activity WHERE user_id = ?", (user_target_id,))
        self.cursor.execute("SELECT * FROM challenges WHERE user_id = ?", (user_target_id,))
        
        total_duration = time.perf_counter() - start_time
        self._print_formatted_result("Pelny profil (Wielokrotne I/O)", total_duration, 1.0)
        self.assertLess(total_duration, 1.0)

if __name__ == '__main__':
    # wywolanie procedur testowych z wylaczonym standardowym wyjsciem unittest
    unittest.main(verbosity=0)
    print("-" * 75)
    print("ZAKONCZONO POMIARY WYDAJNOSCIOWE\n")