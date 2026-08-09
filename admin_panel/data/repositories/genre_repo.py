import sqlite3
from typing import List
from data.models.genre import Genre


class GenresRepository:
    """
    Repozytorium odpowiedzialne za ekstrakcję statystyk dotyczących gatunków.
    Optymalizuje zapytania SQL poprzez unikanie nadmiarowych obliczeń i bezpieczną parametryzację
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        
    @staticmethod
    # Buduje warunek WHERE dla grupy wiekowej, aby filtrować użytkowników w zależności od wieku.
    def _build_age_where_clause(age_group: str, prefix: str = "WHERE") -> str:
        sql_age_calc = """
            (CAST(strftime('%Y', 'now') AS INT) - CAST(strftime('%Y', u.birth_date) AS INT) - 
            (CASE WHEN strftime('%m%d', 'now') < strftime('%m%d', u.birth_date) THEN 1 ELSE 0 END))
        """

        age_filters = {
            "Less than 18": f"{sql_age_calc} < 18",
            "18 - 25": f"{sql_age_calc} BETWEEN 18 AND 25",
            "26 - 40": f"{sql_age_calc} BETWEEN 26 AND 40",
            "41 - 60": f"{sql_age_calc} BETWEEN 41 AND 60",
            "60+": f"{sql_age_calc} >= 60",
        }

        active_filter = age_filters.get(age_group)
        if active_filter:
            return f"{prefix} {active_filter}"

        return "WHERE 1=1" if prefix.upper() == "WHERE" else ""

    @staticmethod
    # Pobiera mapę gatunków (name -> id) z bazy danych.
    def get_genre_map(cursor) -> dict:
        """
        Pobiera mapę gatunków (name -> id) z bazy danych.
        """
        query = "SELECT name, id FROM genres"
        cursor.execute(query)
        return {name: gid for name, gid in cursor.fetchall()}


    def get_all(self, age_group: str = "All") -> List[Genre]:
        """
        Pobiera zagregowane statystyki gatunków z uwzględnieniem filtrów wiekowych.
        Wykorzystuje parametryzowane zapytania w celu uniknięcia SQL Injection.
        """
        cursor = self.conn.cursor()

        # Buduje warunek WHERE dla grupy wiekowej
        where_clause = self._build_age_where_clause(age_group)

        # Zapytanie SQL z CTE (Common Table Expression) dla lepszej czytelności i wydajności
        query = f"""
            WITH FinishedBooks AS (
                SELECT b.id as book_id, b.genre_id, ub.rating, ub.user_id
                FROM user_books ub
                JOIN books b ON ub.book_id = b.id
                JOIN users u ON ub.user_id = u.id
                {where_clause}
                -- Uwzględnia tylko ukończone książki do statystyk gatunkowych
                AND ub.status = 'finished'
            ),
            TotalCount AS (
                -- Zlicza łączną liczbę wszystkich przeczytanych pozycji (rekordów)
                SELECT COUNT(*) as total FROM FinishedBooks
            )
            SELECT
                g.name,
                COUNT(DISTINCT fb.user_id) as readers_count,
                ROUND(AVG(CAST(fb.rating AS FLOAT)), 2) as average_rating,
                COUNT(fb.book_id) as books_count,
                ROUND(CAST(COUNT(fb.book_id) AS FLOAT) / MAX(1, (SELECT total FROM TotalCount)) * 100, 2) as share
            FROM genres g
            LEFT JOIN FinishedBooks fb ON g.id = fb.genre_id
            GROUP BY g.id, g.name
            ORDER BY books_count DESC, readers_count DESC
        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            return [
                Genre(
                    name=row[0],
                    readers=row[1],
                    avg_rating=row[2] if row[2] else 0.0,
                    books_read=row[3],
                    percent_of_total_time=row[4] if row[4] else 0.0,
                )
                for row in rows
            ]
        except sqlite3.Error:
            # W przypadku błędu bazy danych zwracana jest pusta lista
            return []

    def get_declared_preferences(self, age_group: str = "All") -> List[Genre]:
        """
        Zwraca deklarowane preferencje gatunkowe (user_favorite_genres):
        - readers: ilu unikalnych userów wskazało gatunek
        - books_read: liczba wszystkich wskazań (picks)
        - percent_of_total_time: udział % w całkowitej liczbie wskazań
        """
        cursor = self.conn.cursor()

        where_clause = self._build_age_where_clause(age_group)

        query = f"""
            WITH Declared AS (
                SELECT
                    ufg.genre_id,
                    ufg.user_id
                FROM user_favorite_genres ufg
                JOIN users u ON u.id = ufg.user_id
                {where_clause}
            ),
            TotalPicks AS (
                SELECT COUNT(*) AS total FROM Declared
            )
            SELECT
                g.name,
                COUNT(DISTINCT d.user_id) AS readers_count,
                0.0 AS average_rating,
                COUNT(d.user_id) AS picks_count,
                ROUND(
                    CAST(COUNT(d.user_id) AS FLOAT) / MAX(1, (SELECT total FROM TotalPicks)) * 100,
                    2
                ) AS share
            FROM genres g
            LEFT JOIN Declared d ON d.genre_id = g.id
            GROUP BY g.id, g.name
            ORDER BY picks_count DESC, readers_count DESC
        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                Genre(
                    name=row[0],
                    readers=row[1],
                    avg_rating=row[2] if row[2] else 0.0,
                    books_read=row[3],  # tutaj books_read = liczba picks deklaratywnych
                    percent_of_total_time=row[4] if row[4] else 0.0,
                )
                for row in rows
            ]
        except sqlite3.Error:
            return []

    def count_users_by_age_group(self, age_group: str = "All") -> int:
        """Liczy unikalnych użytkowników w wybranej grupie wiekowej"""
        cursor = self.conn.cursor()

        where_clause = self._build_age_where_clause(age_group)

        query = f"""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            {where_clause}
        """

        try:
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error:
            return 0

    def count_declaring_users_by_age_group(self, age_group: str = "All") -> int:
        """Liczy użytkowników, którzy mają co najmniej jedną deklarację ulubionego gatunku."""
        cursor = self.conn.cursor()

        where_clause = self._build_age_where_clause(age_group, prefix="AND")

        query = f"""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            JOIN user_favorite_genres ufg ON ufg.user_id = u.id
            WHERE 1=1
            {where_clause}
        """

        try:
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error:
            return 0
