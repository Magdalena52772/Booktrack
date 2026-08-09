import sqlite3
from datetime import datetime, timedelta


class BookRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def count_books_read(self, period=None):
        """
        Liczy ukończone książki z tabeli relacyjnej user_books. 
        Jeśli podano okres, filtruje wyniki według tego okresu (np. "month" dla ostatnich 30 dni)
        """
        cursor = self.conn.cursor()

        # Buduje warunek filtrowania czasowego
        if period == "month":
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            query = """
                SELECT COUNT(*) 
                FROM user_books 
                WHERE status = 'read' AND finish_date >= ?
            """
            cursor.execute(query, (thirty_days_ago,))
        else:
            query = "SELECT COUNT(*) FROM user_books WHERE status = 'read'"
            cursor.execute(query)

        return cursor.fetchone()[0] or 0


    def get_monthly_reading_trend(self):
        """
        Pobiera trend czytelniczy w formie listy krotek (miesiąc, liczba_ukończonych_książek) dla wykresu liniowego.
        """
        cursor = self.conn.cursor()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        query = """
            SELECT date(timestamp), SUM(pages_read)
            FROM activity
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
        """
        cursor.execute(query, (thirty_days_ago,))
        return cursor.fetchall()


    def get_average_rating(self):
        """Zwraca średnią ocenę wszystkich ocenionych książek z tabeli user_books."""
        cursor = self.conn.cursor()
        query = "SELECT AVG(rating) FROM user_books WHERE rating IS NOT NULL"
        cursor.execute(query)
        result = cursor.fetchone()[0]
        return round(result, 2) if result else 0.0


    def get_highest_rated_books(self, limit=5):
        """Pobiera najlepiej oceniane książki na podstawie średniej ocen użytkowników."""
        cursor = self.conn.cursor()
        query = """
            SELECT b.title, AVG(ub.rating) as avg_rating 
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.rating IS NOT NULL 
            GROUP BY b.id
            ORDER BY avg_rating DESC 
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()
    