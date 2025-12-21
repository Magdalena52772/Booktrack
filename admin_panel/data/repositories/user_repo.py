import sqlite3
from datetime import datetime, timedelta
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_dashboard_metrics(self):
        """Zwraca ogólne statystyki dla Dashboardu."""
        cursor = self.conn.cursor()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        query = """
            SELECT 
                COUNT(id),
                SUM(CASE WHEN register_date >= ? THEN 1 ELSE 0 END),
                AVG(pages_per_day)
            FROM users
        """
        cursor.execute(query, (thirty_days_ago,))
        return cursor.fetchone()
    
    def get_user_report_metrics(self, period="year"):
        """
        Dedykowana metoda dla ReportsView.
        Zwraca: (total_users, new_users_in_period, avg_engagement)
        """
        cursor = self.conn.cursor()
        start_dt = period_start(period)
        
        # Statystyka całkowitej liczby kont (zawsze liczona dla całej bazy)
        cursor.execute("SELECT COUNT(id) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # Statystyka nowych kont w wybranym okresie
        params = []
        where_clause = ""
        if start_dt:
            where_clause = "WHERE register_date >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
        
        cursor.execute(f"SELECT COUNT(id) FROM users {where_clause}", params)
        new_users = cursor.fetchone()[0] or 0

        # Statystyka średniego zaangażowania (pages_per_day)
        cursor.execute(f"SELECT AVG(pages_per_day) FROM users {where_clause}", params)
        avg_engagement = cursor.fetchone()[0] or 0.0

        return total_users, new_users, round(avg_engagement, 1)
    

    def get_favorite_genres(self, user_id: int) -> List[str]:
        """Pobiera nazwy ulubionych gatunków przypisanych do użytkownika."""
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT g.name 
            FROM user_favorite_genres ufg
            JOIN genres g ON ufg.genre_id = g.id
            WHERE ufg.user_id = ?
        """, (user_id,)).fetchall()
        return [r[0] for r in rows]

    def get_all(self, period="year", search_term: str = None) -> List[User]:
        """
        Główna metoda pobierająca listę użytkowników.
        Zsynchronizowana z generatorem (obsługuje kolumnę age).
        """
        cursor = self.conn.cursor()
        since = period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # 1. Budowa zapytania SQL - dodano kolumnę 'age' (u[7])
        query = "SELECT id, name, status, books_read, pages_per_day, last_activity, register_date, age FROM users"
        params = []

        if search_term:
            query += " WHERE (name LIKE ? OR status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term])

        query += " ORDER BY register_date ASC"
        users_data = cursor.execute(query, params).fetchall()

        def parse_date(date_str):
            if not date_str: return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return None

        users = []
        for u in users_data:
            user_id = u[0]

            # 2. Obliczanie liczby przeczytanych książek w danym okresie
            if since_str:
                res_books = cursor.execute("""
                    SELECT COUNT(*) FROM books
                    WHERE user_id = ? AND status = 'finished' AND finish_date >= ?
                """, (user_id, since_str)).fetchone()
                books_read_count = res_books[0] if res_books else 0
            else:
                books_read_count = u[3]

            # 3. Dynamiczne obliczanie pages_per_day
            activity_sql = "SELECT SUM(pages_read), COUNT(DISTINCT date(timestamp)) FROM activity WHERE user_id = ?"
            act_params = [user_id]
            if since_str:
                activity_sql += " AND timestamp >= ?"
                act_params.append(since_str)
            
            res_act = cursor.execute(activity_sql, act_params).fetchone()
            total_pages = res_act[0] or 0
            reading_days = res_act[1] or 1 
            
            dynamic_ppd = round(total_pages / reading_days, 1) if total_pages > 0 else 0.0

            # 4. Mapowanie na model User (z uwzględnieniem wieku)
            users.append(User(
                id=user_id,
                name=u[1],
                status=u[2],
                books_read=books_read_count,
                pages_per_day=dynamic_ppd,
                last_activity=parse_date(u[5]),
                register_date=parse_date(u[6]),
                age=u[7], # Wiek pobrany z kolumny 'age' w bazie
                favorite_genres=self.get_favorite_genres(user_id)
            ))
            
        return users