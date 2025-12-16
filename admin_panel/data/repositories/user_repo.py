import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from data.models.user import User


class UserRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self):
        cursor = self.conn.cursor()

        query = """
        SELECT
            u.id,
            u.name,
            COUNT(DISTINCT a.book_id) AS books_read,
            ROUND(
                CASE 
                    WHEN COUNT(DISTINCT a.timestamp) = 0 THEN 0
                    ELSE SUM(a.pages_read) * 1.0 / COUNT(DISTINCT a.timestamp)
                END
            , 1) AS pages_per_day,
            u.last_activity,
            u.status,
            u.register_date,
            GROUP_CONCAT(DISTINCT g.name) AS genres
        FROM users u
        LEFT JOIN activity a ON a.user_id = u.id
        LEFT JOIN user_favorite_genres uf ON uf.user_id = u.id
        LEFT JOIN genres g ON g.id = uf.genre_id
        GROUP BY u.id
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        users = []
        for row in rows:
            users.append(
                User(
                    id=row[0],
                    name=row[1],
                    books_read=row[2],
                    pages_per_day=row[3],
                    last_activity=datetime.fromisoformat(row[4]) if row[4] else None,
                    status=row[5],
                    register_date=datetime.fromisoformat(row[6]),
                    favorite_genres=row[7].split(",") if row[7] else []
                )
            )

        return users