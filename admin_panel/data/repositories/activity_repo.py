from data.utils.time_periods import period_start
import sqlite3
from datetime import datetime, timedelta

class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_activity_kpi(self, time_filter="week"):
        # Pobieranie wskaźników KPI (Suma stron, Aktywne dni, Średnia sesja)
        cursor = self.conn.cursor()
        params = []
        date_clause = ""
        
        f_type = time_filter.lower()
        
        # Całkowite pominięcie filtra daty dla opcji "all"
        if f_type != "all":
            if f_type == "week":
                # Korekta zakresu do 7 dni (dzisiaj + 6 dni wstecz)
                start_dt = datetime.now() - timedelta(days=6)
                date_clause = "WHERE timestamp >= ?"
                params.append(start_dt.strftime("%Y-%m-%d 00:00:00"))
            else:
                dt = period_start(time_filter)
                if dt:
                    date_clause = "WHERE timestamp >= ?"
                    params.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Pobieranie zsumowanych statystyk
        cursor.execute(f"SELECT SUM(pages_read) FROM activity {date_clause}", params)
        total_pages = cursor.fetchone()[0] or 0

        cursor.execute(f"SELECT COUNT(DISTINCT DATE(timestamp)) FROM activity {date_clause}", params)
        active_days = cursor.fetchone()[0] or 0

        cursor.execute(f"SELECT AVG(pages_read) FROM activity {date_clause}", params)
        avg_session = cursor.fetchone()[0] or 0.0

        return total_pages, active_days, round(avg_session, 1)

    def get_activity_trend(self, time_filter="week"):
        # Pobieranie danych do wykresu trendu dziennego
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

        query = f"""
            SELECT DATE(timestamp), SUM(pages_read)
            FROM activity
            {date_clause}
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) ASC
        """
        cursor.execute(query, params)
        return cursor.fetchall()