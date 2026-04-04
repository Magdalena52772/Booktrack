import sqlite3
from datetime import datetime, timedelta
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start
from data.utils.date_helpers import DateHelper

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row 


    def get_favorite_genres(self, user_id: int) -> List[str]:
        """Pobieranie listy ulubionych gatunków dla konkretnego użytkownika."""
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT g.name 
            FROM user_favorite_genres ufg
            JOIN genres g ON ufg.genre_id = g.id
            WHERE ufg.user_id = ?
        """, (user_id,)).fetchall()
        return [r[0] for r in rows]

    def get_all(self, period="all", search_term: str = None, limit: int = 50, offset: int = 0, sort_by="id", order="DESC") -> List[User]:
        """Pobieranie listy użytkowników z inteligentnym przeliczaniem PPD (Pages Per Day)."""
        cursor = self.conn.cursor()
        
        since = None if period.lower() == "all" else period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # --- Konfiguracja okresu kroczącego ---
        fixed_days = None
        p_lower = period.lower()
        if p_lower == "week":
            fixed_days = 7
        elif p_lower == "month":
            fixed_days = 30
        elif p_lower == "year":
            fixed_days = 365

        # Filtry SQL ograniczają sumę stron (total_pages) tylko do wybranego okresu
        book_filter = "AND finish_date >= ?" if since_str else ""
        act_filter = "AND timestamp >= ?" if since_str else ""

        # Główne zapytanie pobierające dane podstawowe oraz statystyki okresowe
        query = f"""
            SELECT 
                u.id, u.username, u.name, u.email, u.status, u.last_activity, u.date_joined, u.birth_date, u.r_tier,
                (SELECT COUNT(*) FROM books b WHERE b.user_id = u.id AND b.status = 'finished' {book_filter}) as books_count,
                (SELECT SUM(pages_read) FROM activity a WHERE a.user_id = u.id {act_filter}) as total_pages
            FROM users u
        """
        
        params = []
        # Powielenie parametru czasu dla dwóch niezależnych podzapytań
        if since_str:
            params.extend([since_str, since_str])

        # Dodawanie warunków wyszukiwania
        if search_term:
            query += " WHERE (u.username LIKE ? OR u.name LIKE ? OR u.status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term, term])

        allowed_cols = {"id": "u.id", "name": "u.name", "register_date": "u.date_joined"}
        sort_column = allowed_cols.get(sort_by, "u.id")
        query += f" ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        users_data = cursor.execute(query, params).fetchall()
        user_ids = [u['id'] for u in users_data]

        # Pobieranie gatunków (batch)
        genres_map = {}
        if user_ids:
            placeholders = ', '.join(['?'] * len(user_ids))
            genre_query = f"""
                SELECT ufg.user_id, g.name FROM user_favorite_genres ufg
                JOIN genres g ON ufg.genre_id = g.id
                WHERE ufg.user_id IN ({placeholders})
            """
            genre_rows = cursor.execute(genre_query, user_ids).fetchall()
            for row in genre_rows:
                uid, gname = row[0], row[1]
                if uid not in genres_map: genres_map[uid] = []
                genres_map[uid].append(gname)

        users = []
        now = datetime.now()

        for u in users_data:
            # Strony przeczytane w wybranym okresie (zwrócone przez SQL)
            reg_date = DateHelper.to_datetime(u['date_joined'])
            last_act = DateHelper.to_datetime(u['last_activity'])
            
            total_p = u['total_pages'] or 0
            
            # Oblicza całkowity staż konta (dni od rejestracji do dzisiaj)
            days_since_reg = (now - reg_date).days if reg_date else 1
            days_since_reg = max(days_since_reg, 1)

            # --- LOGIKA DZIELNIKA (Retencja i staż) ---
            # Wybór mianownika do obliczenia wskaźnika PPD.
            if p_lower == "all":
                # ŚREDNIA ŻYCIOWA: Dzieli przez całkowity staż konta
                divisor = days_since_reg
            else:
                # ŚREDNIA KROCZĄCA: Dzieli przez wybrany przedział czasu (7, 30, 365, all).
                divisor = fixed_days

            
            rolling_ppd = round(total_p / max(divisor, 1), 1)

            users.append(User(
                id=u['id'],
                username=u['username'],
                name=u['name'],
                email=u["email"],
                status=u['status'],
                birth_date=DateHelper.to_datetime(u['birth_date']), 
                books_read=u['books_count'],
                pages_per_day=rolling_ppd,
                last_activity=last_act,
                date_joined=reg_date,
                r_tier=u['r_tier'],
                favorite_genres=genres_map.get(u['id'], [])
            ))
            
        return users

    def get_global_avg_ppd(self) -> float:
        """Pobiera globalną średnią stron dziennie dla wszystkich użytkowników."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT AVG(pages_per_day) FROM users")
        res = cursor.fetchone()
        val = res[0] if res else 0.0
        return round(val, 1) if val else 0.0

    def count_users(self, search_term: str = None) -> int:
        """Zwraca całkowitą liczbę użytkowników (do paginacji)."""
        cursor = self.conn.cursor()
        query = "SELECT COUNT(*) FROM users"
        params = []
        if search_term:
            query += " WHERE (name LIKE ? OR username LIKE ? OR status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term, term])
        
        cursor.execute(query, params)
        res = cursor.fetchone()
        return res[0] if res else 0
    
    def get_detailed_user_profile(self, user_id: int):
        """
        Pobiera i oblicza kompletny profil użytkownika w jednym miejscu.
        Bezpiecznie obsługuje daty i wiek.
        """
        cursor = self.conn.cursor()
        try:
            # Pobieranie aktualnie czytanych książek
            cursor.execute("SELECT title FROM books WHERE user_id = ? AND status = 'reading' LIMIT 3", (user_id,))
            reading_now = [r[0] for r in cursor.fetchall()]

            # Pobieranie danych bazowych
            cursor.execute("""
                SELECT 
                    u.external_id, u.birth_date, u.last_activity, u.date_joined,
                    (SELECT SUM(pages_read) FROM activity WHERE user_id = u.id) as total_pages,
                    AVG(CAST(c.current_value AS FLOAT) / c.target_value * 100) as avg_progress
                FROM users u
                LEFT JOIN challenges c ON u.id = c.user_id AND c.status = 'active'
                WHERE u.id = ? GROUP BY u.id
            """, (user_id,))
            u_data = cursor.fetchone()

            if not u_data:
                return None

            # Rozpakowanie danych
            ext_id, birth_date_raw, last_act_raw, reg_date_raw, total_pages_sum, avg_progress = u_data
            total_pages_sum = total_pages_sum or 0
            
            # Statystyki aktywności
            streak = self.get_user_streak(user_id)
            real_active_days = self.get_active_reading_days(user_id)
            active_ppd = total_pages_sum / max(1, real_active_days)

            # Obliczanie wieku przy użyciu Helpera
            age = DateHelper.calculate_age(birth_date_raw)

            return {
                "ext_id": ext_id,
                "reading_now": reading_now,
                "total_pages": total_pages_sum,
                "avg_progress": int(avg_progress) if avg_progress else 0,
                "streak": streak,
                "active_ppd": active_ppd,
                "age": age,
                "last_activity": last_act_raw,
                "date_joined": reg_date_raw
            }
        finally:
            cursor.close()
    
    def get_active_reading_days(self, user_id: int) -> int:
        """Liczy ile unikalnych dni użytkownik faktycznie czytał (miał wpis w activity)."""
        cursor = self.conn.cursor()
        query = "SELECT COUNT(DISTINCT date(timestamp)) FROM activity WHERE user_id = ?"
        cursor.execute(query, (user_id,))
        res = cursor.fetchone()
        return max(res[0], 1) if res and res[0] else 1

    def get_user_streak(self, user_id: int) -> int:
        """Oblicza aktualny streak (dni z rzędu z aktywnością)."""
        cursor = self.conn.cursor()
        # Pobiera unikalne daty aktywności użytkownika, posortowane malejąco
        query = """
            SELECT DISTINCT date(timestamp) as activity_date 
            FROM activity 
            WHERE user_id = ? 
            ORDER BY activity_date DESC
        """
        rows = cursor.execute(query, (user_id,)).fetchall()
        
        if not rows:
            return 0
            
        streak = 0
        current_date = datetime.now().date()
        
        # Kiedy była ostatnia aktywność (dzisiaj/wczoraj)
        last_act = datetime.strptime(rows[0][0], "%Y-%m-%d").date()
        if (current_date - last_act).days > 1:
            return 0  # Streak przerwany dawno temu
        
        # Obliczanie ciągłości: sprawdzanie czy kolejna data w rekordach 
        # jest dokładnie o jeden dzień wcześniejsza od poprzedniej.  
        expected_date = last_act
        for row in rows:
            act_date = datetime.strptime(row[0], "%Y-%m-%d").date()
            if act_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break # Przerwa w datach
        return streak
    
    def update_all_streaks(self):
        """Aktualizuje kolumnę current_streak dla wszystkich użytkowników na podstawie aktywności."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM users WHERE is_active = 1")
        user_ids = [row[0] for row in cursor.fetchall()]

        for uid in user_ids:
            actual_streak = self.get_user_streak(uid)
            cursor.execute(
                "UPDATE users SET current_streak = ? WHERE id = ?",
                (actual_streak, uid)
            )
        self.conn.commit()
