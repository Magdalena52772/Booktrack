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
        where_clause = f"WHERE {active_filter}" if active_filter else ""

        # Główne zapytanie wykorzystujące Common Table Expression (CTE) dla przejrzystości i wydajności
        query = f"""
            WITH FilteredData AS (
                SELECT 
                    g.name as genre_name,
                    u.id as user_id,
                    b.id as book_id,
                    CAST(b.rating AS FLOAT) as book_rating
                FROM genres g
                JOIN books b ON g.id = b.genre_id
                JOIN users u ON b.user_id = u.id
                {where_clause}
            ),
            TotalCount AS (
                SELECT COUNT(*) as total FROM FilteredData
            )
            SELECT 
                f.genre_name,
                COUNT(DISTINCT f.user_id) as readers_count,
                ROUND(AVG(f.book_rating), 2) as average_rating,
                COUNT(f.book_id) as books_count,
                ROUND(CAST(COUNT(f.book_id) AS FLOAT) / (SELECT MAX(1, total) FROM TotalCount) * 100, 2) as share
            FROM FilteredData f
            GROUP BY f.genre_name
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