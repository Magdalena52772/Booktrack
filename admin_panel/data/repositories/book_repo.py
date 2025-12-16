import sqlite3

class BookRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def count_books_read(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM activity")
        return cursor.fetchone()[0]