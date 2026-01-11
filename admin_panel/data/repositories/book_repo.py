import sqlite3
from datetime import datetime, timedelta

class BookRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def count_books_read(self, period=None):
        """
        Liczy ukończone książki. 
        Jeśli period='month', liczy tylko te zakończone w ostatnich 30 dniach.
        """
        cursor = self.conn.cursor()
        
        if period == "month":
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            query = "SELECT COUNT(*) FROM books WHERE status = 'finished' AND finish_date >= ?"
            cursor.execute(query, (thirty_days_ago,))
        else:
            query = "SELECT COUNT(*) FROM books WHERE status = 'finished'"
            cursor.execute(query)
            
        return cursor.fetchone()[0]

    def get_monthly_reading_trend(self):
        """
        Pobiera sumę przeczytanych stron dzień po dniu z ostatnich 30 dni.
        Dane idealne do wykresu na dashboardzie.
        """
        cursor = self.conn.cursor()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        query = """
            SELECT date(timestamp), SUM(pages_read)
            FROM activity
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
        """
        cursor.execute(query, (thirty_days_ago,))
        return cursor.fetchall()

    def get_most_popular_genres(self, limit=5):
        """
        Pobiera najpopularniejsze gatunki na podstawie liczby przeczytanych stron.
        """
        cursor = self.conn.cursor()
        query = """
            SELECT g.name, SUM(a.pages_read) as total_pages
            FROM activity a
            JOIN books b ON a.book_id = b.id
            JOIN genres g ON b.genre_id = g.id
            GROUP BY g.id
            ORDER BY total_pages DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()