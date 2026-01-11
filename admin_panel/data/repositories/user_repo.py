import sqlite3
from datetime import datetime, timedelta
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_dashboard_metrics(self):
        # Pobieranie statystyk ogólnych dla panelu głównego
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
        # Pobieranie statystyk dla widoku raportów z obsługą pełnej historii
        cursor = self.conn.cursor()
        
        # Rozróżnienie okresu "all" od filtrów czasowych
        start_dt = None if period.lower() == "all" else period_start(period)
        
        cursor.execute("SELECT COUNT(id) FROM users")
        total_users = cursor.fetchone()[0] or 0

        params = []
        where_clause = ""
        if start_dt:
            where_clause = "WHERE register_date >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
        
        cursor.execute(f"SELECT COUNT(id) FROM users {where_clause}", params)
        new_users = cursor.fetchone()[0] or 0

        cursor.execute(f"SELECT AVG(pages_per_day) FROM users {where_clause}", params)
        avg_engagement = cursor.fetchone()[0] or 0.0

        return total_users, new_users, round(avg_engagement, 1)

    def get_favorite_genres(self, user_id: int) -> List[str]:
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT g.name 
            FROM user_favorite_genres ufg
            JOIN genres g ON ufg.genre_id = g.id
            WHERE ufg.user_id = ?
        """, (user_id,)).fetchall()
        return [r[0] for r in rows]

    def get_all(self, period="all", search_term: str = None, limit: int = 50, offset: int = 0, sort_by="id", order="DESC") -> List[User]:
        cursor = self.conn.cursor()
        
        # Wyznaczenie filtra czasowego dla statystyk wewnątrz obiektu User
        since = None if period.lower() == "all" else period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # Zapytanie o dane profilowe
        query = "SELECT id, name, status, books_read, pages_per_day, last_activity, register_date, age FROM users"
        params = []

        if search_term:
            query += " WHERE (name LIKE ? OR status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term])

        # POPRAWKA SORTOWANIA: Konwersja tekstowego ID na liczbę w SQL
        allowed_cols = {
            "id": "CAST(id AS INTEGER)", 
            "name": "name", 
            "register_date": "register_date",
            "pages_per_day": "pages_per_day"
        }
        sort_column = allowed_cols.get(sort_by, "CAST(id AS INTEGER)")
        safe_order = "DESC" if order.upper() == "DESC" else "ASC"

        query += f" ORDER BY {sort_column} {safe_order}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
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

            # Obliczanie ukończonych książek w wybranym okresie
            book_query = "SELECT COUNT(*) FROM books WHERE user_id = ? AND status = 'finished'"
            book_params = [user_id]
            if since_str:
                book_query += " AND finish_date >= ?"
                book_params.append(since_str)
            
            res_books = cursor.execute(book_query, book_params).fetchone()
            books_read_count = res_books[0] if res_books else 0

            # Wyliczanie dynamicznego Pages/day z tabeli activity
            activity_sql = "SELECT SUM(pages_read), COUNT(DISTINCT date(timestamp)) FROM activity WHERE user_id = ?"
            act_params = [user_id]
            if since_str:
                activity_sql += " AND timestamp >= ?"
                act_params.append(since_str)
            
            res_act = cursor.execute(activity_sql, act_params).fetchone()
            total_pages = res_act[0] or 0
            reading_days = res_act[1] or 1 
            dynamic_ppd = round(total_pages / reading_days, 1) if total_pages > 0 else 0.0

            # Mapowanie na obiekt User
            users.append(User(
                id=user_id,
                name=u[1],
                status=u[2],
                books_read=books_read_count,
                pages_per_day=dynamic_ppd,
                last_activity=parse_date(u[5]),
                register_date=parse_date(u[6]),
                age=u[7],
                favorite_genres=self.get_favorite_genres(user_id)
            ))
            
        return users