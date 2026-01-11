import sqlite3
from typing import List
from data.models.genre import Genre

class GenresRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all(self, age_group: str = "All") -> List[Genre]:
        cursor = self.conn.cursor()
        
        # Mapowanie grup wiekowych na warunki SQL
        age_conditions = {
            "Less than 18": "AND u.age < 18",
            "18 - 25": "AND u.age BETWEEN 18 AND 25",
            "26 - 40": "AND u.age BETWEEN 26 AND 40",
            "41 - 60": "AND u.age BETWEEN 41 AND 60",
            "60+": "AND u.age >= 60"
        }
        
        # Pobiera warunek (jeśli "All" lub brak klucza, zwraca pusty string)
        condition = age_conditions.get(age_group, "")

        # Zapytanie SQL z poprawnymi złączeniami (LEFT JOIN)
        query = f"""
            SELECT 
                g.name, 
                COUNT(DISTINCT u.id) as readers, 
                ROUND(g.avg_rating, 2) as avg_rating, -- Pobieramy realną wartość zapisaną w tabeli
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

        # Lista obiektów Genre
        genres = [
            Genre(
                name=row[0],
                readers=row[1],
                avg_rating=row[2] if row[2] else 0.0, # Zabezpieczenie przed None
                books_read=row[3],
                percent_of_total_time=row[4] if row[4] else 0.0
            )
            for row in rows
        ]
        return genres