import sqlite3
from datetime import datetime, timedelta
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def parse_date(self, date_str):
        """Konwertowanie ciągów znaków na obiekty datetime."""
        if not date_str: 
            return None
        try:
            if len(date_str) > 10:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(date_str, "%Y-%m-%d")
        except: 
            return None

    def get_dashboard_metrics(self):
        """Pobieranie statystyk ogólnych dla panelu głównego."""
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
        """Pobieranie statystyk dla widoku raportów z obsługą pełnej historii."""
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
        """Pobiera listę ulubionych gatunków dla konkretnego użytkownika."""
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT g.name 
            FROM user_favorite_genres ufg
            JOIN genres g ON ufg.genre_id = g.id
            WHERE ufg.user_id = ?
        """, (user_id,)).fetchall()
        return [r[0] for r in rows]

    def get_all(self, period="all", search_term: str = None, limit: int = 50, offset: int = 0, sort_by="id", order="DESC") -> List[User]:
        """Pobieranie listy użytkowników z optymalizacją podzapytań dla uniknięcia pętli SQL."""
        cursor = self.conn.cursor()
        
        since = None if period.lower() == "all" else period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # Definiowanie filtrów czasowych dla podzapytań agregujących
        book_filter = "AND finish_date >= ?" if since_str else ""
        act_filter = "AND timestamp >= ?" if since_str else ""

        # Główne zapytanie pobierające dane podstawowe oraz statystyki okresowe jednym strzałem
        query = f"""
            SELECT 
                u.id, u.name, u.status, u.last_activity, u.register_date, u.birth_date,
                (SELECT COUNT(*) FROM books b WHERE b.user_id = u.id AND b.status = 'finished' {book_filter}) as books_count,
                (SELECT SUM(pages_read) FROM activity a WHERE a.user_id = u.id {act_filter}) as total_pages,
                (SELECT COUNT(DISTINCT date(timestamp)) FROM activity a WHERE a.user_id = u.id {act_filter}) as active_days
            FROM users u
        """
        
        params = []
        # Powielenie parametru czasu dla trzech niezależnych podzapytań
        if since_str:
            params.extend([since_str, since_str, since_str])

        # Dodawanie warunków wyszukiwania
        if search_term:
            query += " WHERE (u.name LIKE ? OR u.status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term])

        # Obsługa bezpiecznego sortowania i paginacji
        allowed_cols = {"id": "u.id", "name": "u.name", "register_date": "u.register_date", "pages_per_day": "u.pages_per_day"}
        sort_column = allowed_cols.get(sort_by, "u.id")
        query += f" ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        users_data = cursor.execute(query, params).fetchall()
        user_ids = [u['id'] for u in users_data]

        # Pobieranie gatunków w jednym zapytaniu dla całej paczki użytkowników
        genres_map = {}
        if user_ids:
            placeholders = ', '.join(['?'] * len(user_ids))
            genre_query = f"""
                SELECT ufg.user_id, g.name 
                FROM user_favorite_genres ufg
                JOIN genres g ON ufg.genre_id = g.id
                WHERE ufg.user_id IN ({placeholders})
            """
            genre_rows = cursor.execute(genre_query, user_ids).fetchall()
            for uid, gname in genre_rows:
                if uid not in genres_map:
                    genres_map[uid] = []
                genres_map[uid].append(gname)

        users = []
        for u in users_data:
            # Obliczanie wskaźnika Pages Per Day na podstawie danych z podzapytań
            total_p = u['total_pages'] or 0
            a_days = u['active_days'] or 1
            dynamic_ppd = round(total_p / a_days, 1) if u['status'] == 'active' else 0.0

            users.append(User(
                id=u['id'],
                name=u['name'],
                status=u['status'],
                birth_date=u['birth_date'], 
                books_read=u['books_count'],
                pages_per_day=dynamic_ppd,
                last_activity=self.parse_date(u['last_activity']),
                register_date=self.parse_date(u['register_date']),
                favorite_genres=genres_map.get(u['id'], [])
            ))
            
        return users