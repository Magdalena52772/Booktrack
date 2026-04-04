from datetime import datetime, timedelta
from data.utils.time_periods import period_start

class StatsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_system_wide_ppd(self, period: str = "all") -> float:
        """
        Liczy średnią PPD identycznie jak w Dashboardzie, 
        ale z uwzględnieniem filtra (period).
        """
        cursor = self.conn.cursor()
        start_dt = period_start(period.lower())
        
        where_clause = ""
        params = []
        if start_dt:
            where_clause = "WHERE timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Logika z Dashboardu: Średnia z dziennych sum każdego użytkownika
        query = f"""
            SELECT IFNULL(AVG(daily_total), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_total
                FROM activity
                {where_clause}
                GROUP BY user_id, DATE(timestamp)
            )
        """
        cursor.execute(query, params)
        res = cursor.fetchone()
        
        # Zwracamy zaokrąglony wynik (np. 23.9)
        return round(float(res[0]), 1) if res and res[0] else 0.0
    
    def get_engagement_stats(self, period="all"):
        """Pobiera dane o streakach (ranking)."""
        cursor = self.conn.cursor()
        # Przykładowy SQL (dostosuj do nazw kolumn w swojej tabeli users)
        query = "SELECT username, current_streak FROM users WHERE current_streak > 0 ORDER BY current_streak DESC LIMIT 3"
        cursor.execute(query)
        rows = cursor.fetchall()
        return {'top_streaks': rows}

#========== REPORTS LOGIC ==========
    def get_dashboard_metrics(self):
        """Pobieranie statystyk ogólnych dla panelu głównego z ostatnich 30 dni."""
        cursor = self.conn.cursor()
        # Definicja progu czasowego dla analizy aktywności i nowych rejestracji
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Wyznaczanie liczby wszystkich użytkowników oraz nowych rejestracji
        cursor.execute("SELECT COUNT(id) FROM users")
        total_users = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(id) FROM users WHERE date_joined >= ?", (thirty_days_ago,))
        new_users = cursor.fetchone()[0] or 0

        # Średnia dzienna stron na użytkownika (tylko dni aktywne)
        # Sumuje strony dla każdego usera w każdym dniu, a potem wyciąga średnią z tych sum.
        avg_query = """
            SELECT IFNULL(AVG(daily_total), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_total
                FROM activity
                WHERE timestamp >= ?
                GROUP BY user_id, DATE(timestamp)
            )
        """
        cursor.execute(avg_query, (thirty_days_ago,))
        avg_pages = cursor.fetchone()[0] or 0.0

        return total_users, new_users, round(float(avg_pages), 1)
    
    def get_user_report_metrics(self, period="year"):
        """
        Pobieranie statystyk zbiorczych dla modułu raportów.
        Oblicza zaangażowanie na podstawie realnej aktywności (średnia dzienna).
        """
        cursor = self.conn.cursor()
        
        # Określenie ramy czasowej i mianownika dla średniej
        p_lower = period.lower()
        start_dt = None if p_lower == "all" else period_start(period)
        
        # Pobieranie podstawowych liczników użytkowników
        cursor.execute("SELECT COUNT(id) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # Liczba nowych użytkowników w wybranym okresie
        new_users = 0
        if start_dt:
            cursor.execute("SELECT COUNT(id) FROM users WHERE date_joined >= ?", 
                          (start_dt.strftime("%Y-%m-%d %H:%M:%S"),))
            new_users = cursor.fetchone()[0] or 0
        else:
            new_users = total_users

        # Średnie zaangażowanie (PPD) w wybranym okresie
        params = []
        act_where = ""
        if start_dt:
            act_where = "WHERE timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query_avg = f"""
            SELECT IFNULL(AVG(daily_total), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_total
                FROM activity 
                {act_where}
                GROUP BY user_id, DATE(timestamp)
            )
        """
        cursor.execute(query_avg, params)
        avg_engagement = cursor.fetchone()[0] or 0.0

        return total_users, new_users, round(float(avg_engagement), 1)
    
    
    def get_report_summary(self, period="all"):
        """Pobiera statystyki zbiorcze gatunków dla modułu raportów."""
        cursor = self.conn.cursor()
        
        start_dt = None if period.lower() == "all" else period_start(period)
        
        params = []
        where_clause = ""
        if start_dt:
            where_clause = "WHERE a.timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query_top = f"""
            SELECT g.name, SUM(a.pages_read) as total_pages
            FROM genres g
            JOIN books b ON b.genre_id = g.id
            JOIN activity a ON a.book_id = b.id
            {where_clause}
            GROUP BY g.id
            ORDER BY total_pages DESC
            LIMIT 1
        """
        
        query_count = f"""
            SELECT COUNT(DISTINCT g.id)
            FROM genres g
            JOIN books b ON b.genre_id = g.id
            JOIN activity a ON a.book_id = b.id
            {where_clause}
        """

        cursor.execute(query_top, params)
        top_res = cursor.fetchone()
        top_genre = top_res[0] if top_res else "None"

        cursor.execute(query_count, params)
        count_res = cursor.fetchone()
        active_count = count_res[0] if count_res else 0

        return top_genre, active_count