from datetime import datetime, timedelta
from data.utils.time_periods import period_start
from data.services.time_filter_service import TimeFilterService


class StatsRepository:
    """
    Repozytorium odpowiedzialne za obliczenia statystyczne i analitykę danych.
    Zapewnia dostęp do zagregowanych wskaźników aktywności oraz raportów systemowych.
    """

    def __init__(self, conn):
        self.conn = conn

    def get_system_wide_ppd(self, period: str = "all") -> float:
        """
        Oblicza średnią liczbę stron przeczytanych dziennie przez użytkownika (PPD).
        Wykorzystuje grupowanie po identyfikatorze użytkownika i dacie dla analityki.
        """
        cursor = self.conn.cursor()

        # Centralizowana logika filtrowania czasowego
        condition, params = TimeFilterService.build_time_filter(period.lower())
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        # Optymalizacja wydajnościowa poprzez wstępne filtrowanie danych w podzapytaniu
        query = f"""
            SELECT IFNULL(AVG(daily_sum), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_sum
                FROM activity
                {where_clause}
                GROUP BY user_id, DATE(timestamp)
            )
        """
        cursor.execute(query, params)
        res = cursor.fetchone()
        return round(float(res[0]), 1) if res and res[0] else 0.0

    def count_books_read(self, period: str = "month") -> int:
        """
        Zlicza unikalne książki, które były aktywnie czytane w danym okresie.
        """
        cursor = self.conn.cursor()
        condition, params = TimeFilterService.build_time_filter(period.lower())
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        query = f"""
            SELECT COUNT(DISTINCT book_id)
            FROM activity
            {where_clause}
        """
        cursor.execute(query, params)
        res = cursor.fetchone()
        return res[0] if res else 0

    def count_active_challenges(self) -> int:
        """Zlicza aktywne wyzwania w całym systemie."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM challenges WHERE status = 'active'")
        res = cursor.fetchone()
        return res[0] if res else 0

    def get_dashboard_metrics(self):
        """
        Pobiera kluczowe metryki dla panelu głównego (Dashboard).
        Zwraca: total_users, new_users, avg_pages, books_read, active_challenges
        """
        cursor = self.conn.cursor()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Pobieranie ogólnej liczby rekordów w tabeli użytkowników
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # pobieranie liczby nowych rejestracji w ostatnim cyklu 30-dniowym
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE date_joined >= ?", (thirty_days_ago,)
        )
        new_users = cursor.fetchone()[0] or 0

        # PPD dla zakresu miesięcznego
        avg_pages = self.get_system_wide_ppd("month")

        # Zliczanie książek przeczytanych w ostatnim miesiącu
        books_read = self.count_books_read("month")
        active_challenges = self.count_active_challenges()

        return total_users, new_users, avg_pages, books_read, active_challenges

    def get_user_report_metrics(self, period="year"):
        """
        Pobiera metryki raportowe dla użytkowników w danym okresie.
        Zwraca: total_users, new_users, avg_engagement
        """
        cursor = self.conn.cursor()

        p_lower = period.lower()
        start_dt = None if p_lower == "all" else period_start(period)

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        new_users = 0
        if start_dt:
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE date_joined >= ?",
                (start_dt.strftime("%Y-%m-%d %H:%M:%S"),),
            )
            new_users = cursor.fetchone()[0] or 0

        avg_engagement = self.get_system_wide_ppd(period)

        return total_users, new_users, avg_engagement


    def get_average_streak(self) -> float:
        """Pobiera średni streak dla wszystkich zarejestrowanych użytkowników."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT AVG(current_streak) FROM users WHERE current_streak IS NOT NULL")
        res = cursor.fetchone()
        return round(float(res[0]), 1) if res and res[0] else 0.0

    def get_top_3_streaks(self):
        """Pobiera top 3 użytkowników z najwyższymi streakami."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT username, current_streak
            FROM users
            WHERE current_streak IS NOT NULL
            ORDER BY current_streak DESC
            LIMIT 3
        """)
        return cursor.fetchall()
    