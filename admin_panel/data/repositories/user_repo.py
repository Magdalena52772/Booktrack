import sqlite3
from datetime import datetime, timedelta
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start

class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row 

    def parse_date(self, date_str):
        """
        Normalizacja formatu daty z bazy SQLite. 
        Obsługuje formaty pełne (z czasem) oraz skrócone (sama data), 
        eliminując błędy wynikające z różnej precyzji zapisu milisekund.
        """
        if not date_str: 
            return None
        try:
            # Ucina mikrosekundy/milisekundy, jeśli występują
            clean_date = date_str.split(".")[0]
            if len(clean_date) > 10:
                return datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(clean_date, "%Y-%m-%d")
        except: 
            return None

    def get_dashboard_metrics(self):
        """Pobieranie statystyk ogólnych dla panelu głównego z ostatnich 30 dni."""
        cursor = self.conn.cursor()
        # Definicja progu czasowego dla analizy aktywności i nowych rejestracji
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        query = """
            SELECT 
                -- Całkowita liczba użytkowników w systemie
                (SELECT COUNT(id) FROM users),
                
                -- Liczba kont zarejestrowanych w ciągu ostatnich 30 dni
                (SELECT COUNT(id) FROM users WHERE date_joined >= ?),
                
                -- Globalne PPD z ostatnich 30 dni:
                -- Suma stron przeczytanych przez WSZYSTKICH użytkowników w tym okresie
                -- podzielona przez liczbę wszystkich kont i okres 30 dni.
                (SELECT 
                    ROUND(
                        CAST(SUM(pages_read) AS FLOAT) / 
                        (MAX(1, (SELECT COUNT(id) FROM users)) * 30.0), 
                    1)
                 FROM activity 
                 WHERE timestamp >= ?)
        """
        
        cursor.execute(query, (thirty_days_ago, thirty_days_ago))
        return cursor.fetchone()
    
    def get_user_report_metrics(self, period="year"):
        """
        Pobieranie statystyk zbiorczych dla modułu raportów.
        Oblicza zaangażowanie na podstawie realnej aktywności wszystkich użytkowników.
        """
        cursor = self.conn.cursor()
        
        # Określenie ramy czasowej i mianownika dla średniej
        p_lower = period.lower()
        start_dt = None if p_lower == "all" else period_start(period)
        
        if p_lower == "week":
            days = 7.0
        elif p_lower == "month":
            days = 30.0
        elif p_lower == "year":
            days = 365.0
        else: # all
            # Dla całego okresu mianownikiem jest średni staż wszystkich kont
            cursor.execute("SELECT AVG(julianday('now') - julianday(date_joined)) FROM users")
            days = cursor.fetchone()[0] or 1.0

        # Całkowita liczba użytkowników (stan na dziś)
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
        # Liczone jako: Suma stron wszystkich użytkowników / (Liczba użytkowników * Liczba dni)
        params = []
        act_where = ""
        if start_dt:
            act_where = "WHERE timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query_avg = f"""
            SELECT 
                CAST(SUM(pages_read) AS FLOAT) / (MAX(1, {total_users}) * {days})
            FROM activity {act_where}
        """
        cursor.execute(query_avg, params)
        avg_engagement = cursor.fetchone()[0] or 0.0

        return total_users, new_users, round(avg_engagement, 1)

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
            query += " WHERE (u.username LIKE ? OR u.status LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term])

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
            # Strony przeczytane W WYBRANYM OKRESIE (zwrócone przez SQL)
            total_p = u['total_pages'] or 0
            reg_date = self.parse_date(u['date_joined'])
            
            # Oblicza całkowity staż konta (dni od rejestracji do dzisiaj)
            days_since_reg = (now - reg_date).days if reg_date else 1
            days_since_reg = max(days_since_reg, 1)

            # --- LOGIKA DZIELNIKA (Sprawiedliwość statystyczna) ---
            # Wybór mianownika do obliczenia wskaźnika PPD.
            if p_lower == "all":
                # ŚREDNIA ŻYCIOWA: Obliczana jako iloraz sumy stron z całej historii aktywności
                # Wskaźnik reprezentuje historyczną wydajność użytkownika.
                divisor = days_since_reg
            else:
                # ŚREDNIA KROCZĄCA: Obliczana jako iloraz sumy stron z wybranego przedziału oraz 
                # liczby dni dla tego okresu (np. 7, 30, 365).
                divisor = fixed_days

            # --- OBLICZENIE KOŃCOWE ---
            # Wyznaczenie wartości PPD z zabezpieczeniem przed dzieleniem przez zero
            # oraz normalizacja wyniku do jednego miejsca po przecinku.
            rolling_ppd = round(total_p / max(divisor, 1), 1)

            users.append(User(
                id=u['id'],
                username=u['username'],
                name=u['name'],
                email=u["email"],
                status=u['status'],
                birth_date=u['birth_date'], 
                books_read=u['books_count'],
                pages_per_day=rolling_ppd,
                last_activity=self.parse_date(u['last_activity']),
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
            query += " WHERE name LIKE ? OR status LIKE ?"
            term = f"%{search_term}%"
            params.extend([term, term])
        
        cursor.execute(query, params)
        res = cursor.fetchone()
        return res[0] if res else 0
    
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
