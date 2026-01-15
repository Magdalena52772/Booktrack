import sqlite3
from typing import List
from data.models.genre import Genre

class GenresRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all(self, age_group: str = "All") -> List[Genre]:
        cursor = self.conn.cursor()
        
        # Wyliczenie wieku w locie: bieżący rok minus rok urodzenia
        sql_age = "(strftime('%Y', 'now') - strftime('%Y', u.birth_date))"
        
        # Mapowanie grup wiekowych na warunki SQL oparte o birth_date
        age_conditions = {
            "Less than 18": f"AND {sql_age} < 18",
            "18 - 25": f"AND {sql_age} BETWEEN 18 AND 25",
            "26 - 40": f"AND {sql_age} BETWEEN 26 AND 40",
            "41 - 60": f"AND {sql_age} BETWEEN 41 AND 60",
            "60+": f"AND {sql_age} >= 60"
        }
        
        condition = age_conditions.get(age_group, "")

        # Zapytanie SQL łączące gatunki z książkami i użytkownikami
        query = f"""
            SELECT 
                g.name, 
                COUNT(DISTINCT u.id) as readers, 
                ROUND(g.avg_rating, 2) as avg_rating,
                COUNT(b.id) as books_cnt,
                g.reading_time_share
            FROM genres g
            LEFT JOIN books b ON g.id = b.genre_id
            LEFT JOIN users u ON b.user_id = u.id {condition}
            GROUP BY g.id, g.name, g.avg_rating, g.reading_time_share
            ORDER BY readers DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()

        # Budowanie listy obiektów Genre
        genres = [
            Genre(
                name=row[0],
                readers=row[1],
                avg_rating=row[2] if row[2] else 0.0,
                books_read=row[3],
                percent_of_total_time=row[4] if row[4] else 0.0
            )
            for row in rows
        ]
        return genres

    def get_report_summary(self, period="all"):
        """Pobiera statystyki zbiorcze gatunków dla modułu raportów."""
        cursor = self.conn.cursor()
        
        from data.utils.time_periods import period_start
        start_dt = None if period.lower() == "all" else period_start(period)
        
        params = []
        where_clause = ""
        if start_dt:
            where_clause = "WHERE a.timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query_top = f"""
            SELECT g.name, SUM(a.pages_read) as total_pages
            FROM genres g
            JOIN books b ON b.genre_id = g.id
            JOIN activity a ON a.book_id = b.id
            {where_clause}
            GROUP BY g.id
            ORDER BY total_pages DESC
            LIMIT 1
        """
        
        query_count = f"""
            SELECT COUNT(DISTINCT g.id)
            FROM genres g
            JOIN books b ON b.genre_id = g.id
            JOIN activity a ON a.book_id = b.id
            {where_clause}
        """

        cursor.execute(query_top, params)
        top_res = cursor.fetchone()
        top_genre = top_res[0] if top_res else "None"

        cursor.execute(query_count, params)
        count_res = cursor.fetchone()
        active_count = count_res[0] if count_res else 0

        return top_genre, active_count