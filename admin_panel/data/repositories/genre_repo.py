import sqlite3
from typing import List
from data.models.genre import Genre
from data.utils.time_periods import period_start

class GenresRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all(self, age_group: str = "All") -> List[Genre]:
        cursor = self.conn.cursor()
        
        sql_age = "(strftime('%Y', 'now') - strftime('%Y', u.birth_date))"
        
        age_conditions = {
            "Less than 18": f"AND {sql_age} < 18",
            "18 - 25": f"AND {sql_age} BETWEEN 18 AND 25",
            "26 - 40": f"AND {sql_age} BETWEEN 26 AND 40",
            "41 - 60": f"AND {sql_age} BETWEEN 41 AND 60",
            "60+": f"AND {sql_age} >= 60"
        }
        
        condition = age_conditions.get(age_group, "")

        total_query = f"""
            SELECT COUNT(b.id) 
            FROM books b 
            JOIN users u ON b.user_id = u.id 
            WHERE 1=1 {condition}
        """
        cursor.execute(total_query)
        total_books_for_group = cursor.fetchone()[0] or 1

        query = f"""
            SELECT 
                g.name, 
                COUNT(DISTINCT u.id) as readers, 
                ROUND(AVG(CAST(b.rating AS FLOAT)), 2) as dynamic_avg_rating, -- Dynamiczne liczenie
                COUNT(b.id) as books_cnt,
                ROUND(CAST(COUNT(b.id) AS FLOAT) / {total_books_for_group} * 100, 2) as dynamic_share
            FROM genres g
            JOIN books b ON g.id = b.genre_id
            JOIN users u ON b.user_id = u.id
            WHERE 1=1 {condition}
            GROUP BY g.id, g.name
            ORDER BY readers DESC, books_cnt DESC
        """
        
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