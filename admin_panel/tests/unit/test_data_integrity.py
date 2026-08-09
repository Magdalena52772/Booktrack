import sqlite3
import sys
import unittest
import inspect
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
    """

    @classmethod
    def setUpClass(cls):
        cls.conn = get_connection()
        cls.cursor = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    # --- KATEGORIA: REALIZM DANYCH I STATYSTYKA ---

    def test_user_age_distribution(self):
        self.cursor.execute("SELECT birth_date FROM users")
        birth_dates = [datetime.strptime(row[0].split()[0], "%Y-%m-%d") for row in self.cursor.fetchall()]
        ages = [(datetime.now() - bd).days // 365 for bd in birth_dates]
        avg_age = sum(ages) / len(ages) if ages else 0
        self.assertTrue(25 <= avg_age <= 45)

    def test_genre_stats_logic(self):
        self.cursor.execute("SELECT SUM(reading_time_share) FROM genres")
        total_share = self.cursor.fetchone()[0] or 0
        self.assertTrue(99.0 <= total_share <= 101.0)

    def test_pages_read_limit(self):
        self.cursor.execute("SELECT MAX(pages_read) FROM activity")
        max_p = self.cursor.fetchone()[0] or 0
        self.assertLessEqual(max_p, 300)

    def test_inactive_user_ratio(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'inactive'")
        inactive = self.cursor.fetchone()[0]
        ratio = (inactive / total) * 100 if total > 0 else 0
        self.assertTrue(2 <= ratio <= 15)

    def test_weekend_multiplier_effect(self):
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) IN ('0', '6')")
        avg_we = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT AVG(pages_read) FROM activity WHERE strftime('%w', timestamp) NOT IN ('0', '6')")
        avg_wd = self.cursor.fetchone()[0] or 0
        self.assertGreater(avg_we, avg_wd)

    def test_age_genre_correlation(self):
        query = """
            SELECT g.name
            FROM users u
            JOIN user_books ub ON ub.user_id = u.id
            JOIN books b ON b.id = ub.book_id
            JOIN genres g ON g.id = b.genre_id
            WHERE (strftime('%Y','now') - strftime('%Y',u.birth_date)) < 18
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if not rows:
            return
        anomalies = [r[0] for r in rows if r[0] in ["Biography", "Crime", "Historical fiction"]]
        ratio = len(anomalies) / len(rows)
        self.assertLess(ratio, 0.20)

    # --- KATEGORIA: INTEGRALNOŚĆ RELACYJNA I WIĘZY ---

    def test_birth_date_not_null_constraint(self):
        self.cursor.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO users (password, username, date_joined) VALUES ('p','u','2026-01-01')")
        self.conn.rollback()

    def test_unique_user_id(self):
        test_id = 99999
        user_data = (test_id, "h", "t", 0, 0, "2026-01-01", "1990-01-01")
        query = "INSERT INTO users (id, password, username, is_superuser, is_staff, date_joined, birth_date) VALUES (?,?,?,?,?,?,?)"
        self.cursor.execute(query, user_data)
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(query, user_data)
        self.conn.rollback()

    def test_foreign_key_constraint(self):
        self.cursor.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO user_books (user_id, book_id, current_page, status) VALUES (999999, 1, 0, 'reading')")
        self.conn.rollback()

    def test_orphan_records_activity(self):
        self.cursor.execute("SELECT COUNT(*) FROM activity WHERE user_id NOT IN (SELECT id FROM users)")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_genre_integrity_constraint(self):
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE genre_id NOT IN (SELECT id FROM genres)")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    # --- KATEGORIA: SPÓJNOŚĆ LOGICZNA I STATUSY ---

    def test_inactive_anomalies(self):
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'inactive' AND pages_per_day > 0")
        self.assertEqual(self.cursor.fetchone()[0], 0)
        query = "SELECT COUNT(*) FROM users u JOIN activity a ON u.id = a.user_id WHERE u.status = 'inactive' AND a.timestamp > datetime('now', '-6 months')"
        self.cursor.execute(query)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_books_consistency(self):
        query = """
        SELECT
            u.books_read,
            (
                SELECT COUNT(*)
                FROM user_books ub
                WHERE ub.user_id = u.id
                AND ub.status='finished'
            )
        FROM users u
        """
        self.cursor.execute(query)
        for cached, actual in self.cursor.fetchall():
            self.assertEqual(cached, actual)

    def test_activity_timestamps(self):
        query = "SELECT COUNT(*) FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp < u.date_joined"
        self.cursor.execute(query)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_book_progress_logic(self):
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM user_books ub
            JOIN books b ON b.id = ub.book_id
            WHERE ub.current_page > b.total_pages
            OR ub.current_page < 0
        """)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_external_id_uniqueness(self):
        self.cursor.execute("SELECT COUNT(external_id), COUNT(DISTINCT external_id) FROM users")
        total, distinct = self.cursor.fetchone()
        self.assertEqual(total, distinct)

    def test_user_books_have_existing_books(self):
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM user_books ub
            LEFT JOIN books b ON b.id = ub.book_id
            WHERE b.id IS NULL
        """)
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_challenge_status_logic(self):
        self.cursor.execute("SELECT target_value, current_value, status, end_date FROM challenges")
        now = datetime.now()
        for target, progress, status, end_date_str in self.cursor.fetchall():
            clean_date = end_date_str.split(".")[0] if "." in end_date_str else end_date_str
            try:
                end_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_date = datetime.strptime(clean_date, "%Y-%m-%d")
            if progress >= target: self.assertEqual(status, "finished")
            elif end_date < now: self.assertEqual(status, "failed")
            else: self.assertEqual(status, "active")

    def test_empty_book_titles(self):
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE title IS NULL OR title = '' OR genre_id IS NULL")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_inactive_users_no_recent_sessions(self):
        limit = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
        query = "SELECT COUNT(*) FROM users u JOIN activity a ON u.id = a.user_id WHERE u.status = 'inactive' AND a.timestamp > ?"
        self.cursor.execute(query, (limit,))
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_reading_books_distribution(self):
        self.cursor.execute("""
            SELECT reading_count, COUNT(*) AS users_count
            FROM (SELECT u.id, COUNT(ub.id) AS reading_count FROM users u
            LEFT JOIN user_books ub ON u.id = ub.user_id AND ub.status = 'reading' GROUP BY u.id)
            GROUP BY reading_count ORDER BY reading_count
        """)
        rows = self.cursor.fetchall()
        total_users, users_without = 0, 0
        for reading_count, users_count in rows:
            total_users += users_count
            if reading_count == 0: users_without = users_count
        percentage = (users_without / total_users * 100) if total_users > 0 else 0
        self.assertLess(percentage, 70)

    def test_active_users_have_reading_books(self):
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM users u
            LEFT JOIN user_books ub
                ON ub.user_id = u.id AND ub.status = 'reading'
            WHERE u.status = 'active'
            GROUP BY u.id
            HAVING COUNT(ub.id) = 0
        """)
        users_without_reading = len(self.cursor.fetchall())

        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        total_active = self.cursor.fetchone()[0]

        ratio = (users_without_reading / total_active) * 100 if total_active > 0 else 0
        print(
            f"[CHECK] Active users without currently reading: "
            f"{users_without_reading}/{total_active} ({ratio:.2f}%)"
        )
        self.assertLess(ratio, 20)

    def test_random_reading_users(self):
        self.cursor.execute("""
            SELECT u.id, u.username, b.title
            FROM users u
            JOIN user_books ub ON ub.user_id = u.id
            JOIN books b ON b.id = ub.book_id
            WHERE ub.status='reading'
            LIMIT 20
        """)

        rows = self.cursor.fetchall()

        self.assertGreater(len(rows), 0)

    def test_recent_started_reading_users(self):
        self.cursor.execute("""
            SELECT DISTINCT
                u.id,
                u.username
            FROM activity a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.timestamp DESC
            LIMIT 20
        """)

        users = self.cursor.fetchall()

        missing = []

        for user_id, username in users:
            self.cursor.execute("""
                SELECT 1
                FROM user_books
                WHERE user_id = ?
                AND status = 'reading'
                LIMIT 1
            """, (user_id,))

            if self.cursor.fetchone() is None:
                missing.append(username)

        self.assertLess(len(missing), len(users) * 0.5)


    def test_debug_book_progress(self):
        self.cursor.execute("""
            SELECT
                ub.user_id,
                ub.book_id,
                b.title,
                ub.current_page,
                b.total_pages
            FROM user_books ub
            JOIN books b
                ON ub.book_id = b.id
            WHERE ub.current_page > b.total_pages
            OR ub.current_page < 0
        """)

        rows = self.cursor.fetchall()

        print("\n" + "=" * 80)
        print("BŁĘDNE POSTĘPY KSIĄŻEK")
        print("=" * 80)

        if not rows:
            print("Brak błędów.")
        else:
            for user_id, book_id, title, current_page, total_pages in rows:
                print(
                    f"User: {user_id:<5} "
                    f"Book: {book_id:<5} "
                    f"'{title}' "
                    f"current_page={current_page} "
                    f"total_pages={total_pages}"
                )

        self.assertEqual(len(rows), 0)


    def test_debug_book_progress_details(self):
        self.cursor.execute("""
            SELECT
                ub.user_id,
                b.title,
                ub.current_page,
                b.total_pages,
                ub.status,
                ub.finish_date
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.current_page > b.total_pages
        """)

        rows = self.cursor.fetchall()

        print("\n===== SZCZEGÓŁY =====")

        for row in rows:
            print(row)


    def test_debug_activity_sum(self):
        print("\n===== SUMA SESJI =====")

        self.cursor.execute("""
            SELECT
                ub.user_id,
                ub.book_id,
                ub.current_page,
                b.total_pages,
                SUM(a.pages_read) AS pages
            FROM user_books ub
            JOIN books b
                ON b.id = ub.book_id
            LEFT JOIN activity a
                ON a.user_id = ub.user_id
            AND a.book_id = ub.book_id
            GROUP BY ub.user_id, ub.book_id
            HAVING pages > b.total_pages
        """)

        rows = self.cursor.fetchall()

        for row in rows:
            print(dict(row))

        self.assertEqual(len(rows), 0)


    def test_activity_after_finish_date(self):

        self.cursor.execute("""
            SELECT
                ub.user_id,
                ub.book_id,
                ub.finish_date,
                MAX(a.timestamp)
            FROM user_books ub
            JOIN activity a
                ON a.user_id = ub.user_id
            AND a.book_id = ub.book_id
            WHERE ub.finish_date IS NOT NULL
            GROUP BY ub.user_id, ub.book_id
        """)

        bad = []

        for user_id, book_id, finish_dt, last_session in self.cursor.fetchall():
            if last_session > finish_dt:
                bad.append((user_id, book_id, finish_dt, last_session))

        print("\n=== SESJE PO ZAKOŃCZENIU ===")

        for b in bad:
            print(b)

        self.assertEqual(len(bad), 0)


    def test_same_book_multiple_finished(self):

        self.cursor.execute("""
            SELECT
                user_id,
                book_id,
                COUNT(*)
            FROM activity
            GROUP BY user_id, book_id
            HAVING COUNT(*) > 0
        """)

        rows = self.cursor.fetchall()

        print("\n=== KSIĄŻKI Z SESJAMI ===")

        for row in rows[:20]:
            print(row)


    def test_debug_one_overflow(self):
        """
        Pokazuje pierwszą książkę, dla której suma activity > total_pages
        oraz stan user_books.
        """

        self.cursor.execute("""
            SELECT
                ub.user_id,
                ub.book_id,
                b.title,
                ub.current_page,
                b.total_pages,
                ub.status,
                ub.finish_date,
                COALESCE(SUM(a.pages_read),0) AS pages
            FROM user_books ub
            JOIN books b
                ON b.id = ub.book_id
            LEFT JOIN activity a
                ON a.user_id = ub.user_id
            AND a.book_id = ub.book_id
            GROUP BY
                ub.user_id,
                ub.book_id
            HAVING pages > b.total_pages
            LIMIT 1
        """)

        row = self.cursor.fetchone()

        if row is None:
            print("\nBrak overflowów.")
            return

        print("\n" + "=" * 90)
        print("ZNALEZIONO OVERFLOW")
        print("=" * 90)

        print(f"user_id      = {row['user_id']}")
        print(f"book_id      = {row['book_id']}")
        print(f"title        = {row['title']}")
        print(f"status       = {row['status']}")
        print(f"current_page = {row['current_page']}")
        print(f"total_pages  = {row['total_pages']}")
        print(f"finish_date  = {row['finish_date']}")
        print(f"SUM(activity)= {row['pages']}")

        self.cursor.execute("""
            SELECT
                timestamp,
                pages_read
            FROM activity
            WHERE user_id = ?
            AND book_id = ?
            ORDER BY timestamp
        """, (row["user_id"], row["book_id"]))

        print("\nHistoria sesji:\n")

        total = 0

        for ts, pages in self.cursor.fetchall():
            total += pages

            marker = ""
            if total > row["total_pages"]:
                marker = "   <<< PRZEKROCZENIE"

            print(
                f"{ts} | +{pages:3} | suma={total:4}{marker}"
            )

        self.fail("Overflow znaleziony.")


class LogicUnitTests(unittest.TestCase):
    def test_consistency_score_logic(self):
        self.assertEqual((6 / 30) * 100, 20.0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print(f"{'RAPORT Z TESTÓW INTEGRALNOŚCI SYSTEMU BOOKTRACK':^80}")
    print("=" * 80)
    print(f"{'ID Metody Testowej':<45} | {'Status':<12} | {'Wynik'}")
    print("-" * 80)

    test_classes = [obj for _, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass) 
                    if issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase]

    fail_names = {t[0]._testMethodName for t in result.failures}
    err_names = {t[0]._testMethodName for t in result.errors}

    for cls in test_classes:
        methods = [
            m
            for m, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
            if m.startswith("test_")
        ]

        for m_name in methods:
            status = "PASSED ✅"

            if m_name in fail_names:
                status = "FAILED ❌"
            elif m_name in err_names:
                status = "ERROR ⚠️"

            print(f"{m_name:<45} | {status:<12} | Pozytywny")

    print("-" * 80)
    print(f"PODSUMOWANIE: Wykonano {result.testsRun} testów. Błędy: {len(result.errors)}, Niepowodzenia: {len(result.failures)}")
    print(f"Status końcowy: {'SUKCES (OK)' if result.wasSuccessful() else 'WYKRYTO NIEPRAWIDŁOWOŚCI'}")
    print("=" * 80 + "\n")
