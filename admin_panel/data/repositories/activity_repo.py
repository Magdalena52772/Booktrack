# data/repositories/activity_repo.py
from data.utils.time_periods import period_start
import sqlite3
from datetime import datetime, timedelta

class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_activity_kpi(self, time_filter="week"):
        """
        Pobieranie wskaźników KPI
        """
        cursor = self.conn.cursor()
        params = []
        date_clause = ""
        f_type = time_filter.lower()
        
        if f_type != "all":
            if f_type == "week":
                start_dt = datetime.now() - timedelta(days=6)
                date_clause = "WHERE timestamp >= ?"
                params.append(start_dt.strftime("%Y-%m-%d 00:00:00"))
            else:
                dt = period_start(time_filter)
                if dt:
                    date_clause = "WHERE timestamp >= ?"
                    params.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Zastosowanie COALESCE i IFNULL (stabilność danych)
        cursor.execute(f"SELECT IFNULL(SUM(pages_read), 0) FROM activity {date_clause}", params)
        total_pages = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(DISTINCT DATE(timestamp)) FROM activity {date_clause}", params)
        active_days = cursor.fetchone()[0] or 0

        cursor.execute(f"SELECT IFNULL(AVG(pages_read), 0.0) FROM activity {date_clause}", params)
        avg_session = cursor.fetchone()[0]

        return int(total_pages), active_days, round(float(avg_session), 1)

    def get_activity_trend(self, time_filter="week"):
        """
        Pobieranie trendu aktywności
        """
        cursor = self.conn.cursor()
        params = []
        date_clause = ""
        f_type = time_filter.lower()
        
        group_by = "DATE(timestamp)"
        
        if f_type == "all":
            group_by = "STRFTIME('%Y-%m', timestamp)"
        else:
            if f_type == "week":
                start_dt = datetime.now() - timedelta(days=6)
                date_clause = "WHERE timestamp >= ?"
                params.append(start_dt.strftime("%Y-%m-%d 00:00:00"))
            else:
                dt = period_start(time_filter)
                if dt:
                    date_clause = "WHERE timestamp >= ?"
                    params.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

        query = f"""
            SELECT {group_by} as period, SUM(pages_read) as daily_sum
            FROM activity
            {date_clause}
            GROUP BY period
            ORDER BY period ASC
        """
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Brak danych zwróci pustą listę
        return results if results else []