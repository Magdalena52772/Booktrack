from datetime import datetime, timedelta
import sqlite3

class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_activity_kpi(self, time_filter="week"):
        cursor = self.conn.cursor()
        now = datetime.now()

        if time_filter == "week":
            start = now - timedelta(days=7)
        elif time_filter == "month":
            start = now - timedelta(days=30)
        elif time_filter == "year":
            start = now - timedelta(days=365)
        else:
            start = datetime.min

        start_str = start.strftime("%Y-%m-%d %H:%M:%S")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            SELECT COUNT(DISTINCT book_id) 
            FROM activity 
            WHERE timestamp BETWEEN ? AND ?
        """, (start_str, now_str))
        books_count = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp))
            FROM activity
            WHERE timestamp BETWEEN ? AND ?
        """, (start_str, now_str))
        active_days = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM challenges
            WHERE status = 'active' AND start_date <= ? AND end_date >= ?
        """, (now_str, start_str))
        challenges_count = cursor.fetchone()[0] or 0

        return books_count, active_days, challenges_count
