import sqlite3
from typing import List
from data.models.genre import Genre

class GenresRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all(self) -> List[Genre]:
        cursor = self.conn.cursor()
        query = """
            SELECT name, readers, avg_rating, books_read, reading_time_share
            FROM genres
            ORDER BY name
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        genres = [
            Genre(
                name=row[0],
                readers=row[1],
                avg_rating=row[2],
                books_read=row[3],
                percent_of_total_time=row[4]
            )
            for row in rows
        ]
        return genres