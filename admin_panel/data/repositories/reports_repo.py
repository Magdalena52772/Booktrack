import sqlite3

from data.services.time_filter_service import TimeFilterService


class ReportsRepository:
    """
    Repozytorium odpowiedzialne za generowanie raportów i statystyk systemowych.
    Zapewnia dostęp do zagregowanych danych dotyczących aktywności użytkowników,
    książek i gatunków.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _time_filter(self, period: str):
        condition, params = TimeFilterService.build_time_filter(period.lower())
        where = f"WHERE 1=1 {condition}" if condition else ""
        return where, params

    # ==========================================================
    # TOP READERS
    # ==========================================================

    def get_top_readers(self, period="all", limit=20):
        """
        Pobiera listę topowych czytelników w danym okresie.
        """
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            WITH filtered_activity AS (
                SELECT
                    user_id,
                    book_id,
                    pages_read
                FROM activity
                {where}
            )
            SELECT
                u.username,
                u.current_streak,
                COUNT(DISTINCT fa.book_id) AS books_read,
                IFNULL(SUM(fa.pages_read), 0) AS pages_read,
                IFNULL(MAX(fa.pages_read), 0) AS longest_session,
                DATE(u.date_joined)
            FROM users u
            LEFT JOIN filtered_activity fa
                ON fa.user_id = u.id
            GROUP BY
                u.id,
                u.username,
                u.current_streak,
                DATE(u.date_joined)
            HAVING COUNT(fa.user_id) > 0
            ORDER BY
                pages_read DESC,
                u.current_streak DESC
            LIMIT ?
        """

        cursor.execute(query, (*params, limit))
        return cursor.fetchall()

# ==========================================================
# MOST POPULAR BOOKS
# ==========================================================

    def get_top_books(self, period="all", limit=20):
        """ Pobiera listę najpopularniejszych książek w danym okresie.
        Popularność jest mierzona liczbą unikalnych użytkowników, 
        którzy przeczytali książkę w tym okresie."""
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            WITH active_books AS (
                SELECT DISTINCT
                    user_id,
                    book_id
                FROM activity
                {where}
            )

            SELECT
                b.title,

                COUNT(DISTINCT CASE
                    WHEN ub.status = 'reading'
                    THEN ub.user_id
                END) AS reading,

                COUNT(DISTINCT CASE
                    WHEN ub.status = 'finished'
                    THEN ub.user_id
                END) AS finished,

                ROUND(AVG(ub.rating), 2) AS rating,

                g.name AS genre

            FROM active_books ab

            JOIN user_books ub
                ON ub.user_id = ab.user_id
            AND ub.book_id = ab.book_id

            JOIN books b
                ON b.id = ab.book_id

            JOIN genres g
                ON g.id = b.genre_id

            GROUP BY
                b.id,
                b.title,
                g.name

            ORDER BY
                finished DESC,
                reading DESC,
                rating DESC

            LIMIT ?
        """

        cursor.execute(query, (*params, limit))
        return cursor.fetchall()

    # ==========================================================
    # ACTIVITY SUMMARY
    # ==========================================================

    def get_activity_summary(self, period="all"):
        """
        Pobiera podsumowanie aktywności użytkowników w danym okresie.
        """
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            SELECT
                IFNULL(SUM(pages_read), 0),
                COUNT(*),
                COUNT(DISTINCT user_id),
                IFNULL(ROUND(AVG(pages_read), 1), 0)
            FROM activity
            {where}
        """

        cursor.execute(query, params)
        return cursor.fetchone()

    def get_top_reader(self, period="all"):
        """
        Pobiera najaktywniejszego czytelnika w danym okresie.
        """
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            SELECT
                u.username,
                SUM(a.pages_read) AS pages
            FROM activity a
            JOIN users u
                ON u.id = a.user_id
            {where}
            GROUP BY
                u.id,
                u.username
            ORDER BY
                pages DESC
            LIMIT 1
        """

        cursor.execute(query, params)
        return cursor.fetchone() or ("-", 0)

    def get_most_active_day(self, period="all"):
        """
        Pobiera dzień z największą aktywnością (najwięcej przeczytanych stron) w danym okresie."""
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            SELECT
                DATE(timestamp),
                SUM(pages_read)
            FROM activity
            {where}
            GROUP BY
                DATE(timestamp)
            ORDER BY
                SUM(pages_read) DESC
            LIMIT 1
        """

        cursor.execute(query, params)
        return cursor.fetchone() or ("-", 0)

    # ==========================================================
    # GENRE TRENDS
    # ==========================================================

    def get_top_genres(self, period="all"):
        """
        Pobiera listę najpopularniejszych gatunków w danym okresie.
        Popularność jest mierzona liczbą przeczytanych stron w danym gatunku.
        """
        cursor = self.conn.cursor()

        where, params = self._time_filter(period)

        query = f"""
            SELECT
                g.name,
                IFNULL(SUM(a.pages_read), 0) AS pages
            FROM activity a
            JOIN books b
                ON b.id = a.book_id
            JOIN genres g
                ON g.id = b.genre_id
            {where}
            GROUP BY
                g.id,
                g.name
            ORDER BY
                pages DESC
        """

        cursor.execute(query, params)
        return cursor.fetchall()
    