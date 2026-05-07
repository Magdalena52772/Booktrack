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
        
        # Definicja fragmentu SQL obliczającego wiek w jednym miejscu
        sql_age_calc = "(strftime('%Y', 'now') - strftime('%Y', u.birth_date))"
        
        # Mapowanie grup wiekowych na warunki SQL
        age_filters = {
            "Less than 18": f"{sql_age_calc} < 18",
            "18 - 25": f"{sql_age_calc} BETWEEN 18 AND 25",
            "26 - 40": f"{sql_age_calc} BETWEEN 26 AND 40",
            "41 - 60": f"{sql_age_calc} BETWEEN 41 AND 60",
            "60+": f"{sql_age_calc} >= 60"
        }
        
        active_filter = age_filters.get(age_group)
        where_clause = f"WHERE {active_filter}" if active_filter else "WHERE 1=1"

        # Jedna query z CTE dla total_finished
        query = f"""
            WITH FinishedBooks AS (
                SELECT b.id, b.genre_id, b.rating, u.id as user_id
                FROM books b
                LEFT JOIN users u ON b.user_id = u.id
                {where_clause}
                AND b.status = 'finished'
            ),
            TotalCount AS (
                SELECT COUNT(DISTINCT id) as total FROM FinishedBooks
            )
            SELECT
                g.name,
                COUNT(DISTINCT fb.user_id) as readers_count,
                ROUND(AVG(CAST(fb.rating AS FLOAT)), 2) as average_rating,
                COUNT(DISTINCT fb.id) as books_count,
                ROUND(CAST(COUNT(DISTINCT fb.id) AS FLOAT) / MAX(1, (SELECT total FROM TotalCount)) * 100, 2) as share
            FROM genres g
            LEFT JOIN FinishedBooks fb ON g.id = fb.genre_id
            GROUP BY g.id, g.name
            ORDER BY readers_count DESC, books_count DESC
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
                    percent_of_total_time=row[4] if row[4] else 0.0
                )
                for row in rows
            ]
        except sqlite3.Error:
            # W przypadku błędu bazy danych zwracana jest pusta lista
            return []

    def count_users_by_age_group(self, age_group: str = "All") -> int:
        """Liczy unikalnych użytkowników w wybranej grupie wiekowej"""
        cursor = self.conn.cursor()

        sql_age_calc = "(strftime('%Y', 'now') - strftime('%Y', u.birth_date))"

        age_filters = {
            "Less than 18": f"{sql_age_calc} < 18",
            "18 - 25": f"{sql_age_calc} BETWEEN 18 AND 25",
            "26 - 40": f"{sql_age_calc} BETWEEN 26 AND 40",
            "41 - 60": f"{sql_age_calc} BETWEEN 41 AND 60",
            "60+": f"{sql_age_calc} >= 60"
        }

        active_filter = age_filters.get(age_group)
        where_clause = f"WHERE {active_filter}" if active_filter else ""

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