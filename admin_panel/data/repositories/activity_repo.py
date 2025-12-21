from data.utils.time_periods import period_start
from datetime import datetime, timedelta
import sqlite3

class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_activity_kpi(self, time_filter="week"):
        cursor = self.conn.cursor()
        start_dt = period_start(time_filter)
        
        # Obsługa przypadku "all" (start_dt is None)
        params = []
        date_clause = ""
        if start_dt:
            date_clause = "WHERE timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Statystyka książek
        cursor.execute(f"SELECT COUNT(DISTINCT book_id) FROM activity {date_clause}", params)
        books_count = cursor.fetchone()[0] or 0

        # Statystyka aktywnych dni
        cursor.execute(f"SELECT COUNT(DISTINCT DATE(timestamp)) FROM activity {date_clause}", params)
        active_days = cursor.fetchone()[0] or 0

        # Wyzwania (niezależne od daty aktywności, tylko status)
        cursor.execute("SELECT COUNT(*) FROM challenges WHERE status = 'active'")
        challenges_count = cursor.fetchone()[0] or 0

        return books_count, active_days, challenges_count

    def get_activity_trend(self, time_filter="week"):
        cursor = self.conn.cursor()
        start_dt = period_start(time_filter)
        
        params = []
        date_clause = ""
        if start_dt:
            date_clause = "WHERE timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query = f"""
            SELECT DATE(timestamp), SUM(pages_read)
            FROM activity
            {date_clause}
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) ASC
        """
        cursor.execute(query, params)
        return cursor.fetchall()