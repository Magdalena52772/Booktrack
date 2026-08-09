import sqlite3
from datetime import datetime
from typing import List
from data.models.user import User
from data.utils.time_periods import period_start
from data.utils.helpers.date_helpers import DateHelper
from data.services.user_performance_service import UserPerformanceService


class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def get_favorite_genres(self, user_id: int) -> List[str]:
        """Pobieranie listy ulubionych gatunków dla konkretnego użytkownika."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT g.name 
            FROM user_favorite_genres ufg
            JOIN genres g ON ufg.genre_id = g.id
            WHERE ufg.user_id = ?
        """,
            (user_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_all(
        self,
        period="all",
        search_term: str = None,
        limit: int = 50,
        offset: int = 0,
        sort_by="id",
        order="DESC",
    ) -> List[User]:
        """Pobieranie listy użytkowników z przeliczaniem Systematic PPD (Time Based)."""
        cursor = self.conn.cursor()

        since = None if period.lower() == "all" else period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # Konfiguracja okresu kroczącego dla Systematic PPD (brutalna średnia, suma stron / liczba dni w wybranym filtrze)
        p_lower = period.lower()
        fixed_days = {"week": 7, "month": 30, "year": 365}.get(p_lower)

        # Dynamiczne filtry (Time + Search)
        where_clauses = []
        params = []

        # Filtry czasu dla subqueries
        act_time_filter = "AND timestamp >= ?" if since_str else ""
        if since_str:
            params.insert(0, since_str)

        # Dodawanie warunków wyszukiwania
        if search_term:
            where_clauses.append(
                "(u.username LIKE ? OR u.email LIKE ? OR u.name LIKE ? OR u.status LIKE ? OR u.id LIKE ?)"
            )
            term = f"%{search_term}%"
            params.extend([term, term, term, term, term])

        # Składanie głównego WHERE
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Główne zapytanie (JOIN -> WHERE -> GROUP -> ORDER -> LIMIT)
        allowed_cols = {
            "id": "u.id",
            "name": "u.name",
            "register_date": "u.date_joined",
        }
        sort_column = allowed_cols.get(sort_by, "u.id")

        query = f"""
            SELECT
                u.id, u.username, u.name, u.email, u.status, u.last_activity,
                u.date_joined, u.birth_date, u.r_tier,
                (SELECT COUNT(*) FROM user_books ub WHERE ub.user_id = u.id AND ub.status = 'finished') AS books_count,
                COALESCE((SELECT SUM(pages_read) FROM activity WHERE user_id = u.id {act_time_filter}), 0) AS total_pages
            FROM users u
            {where_sql}
            ORDER BY {sort_column} {order}
            LIMIT ? OFFSET ?
        """

        # Łączenie parametrów: [time filter] + [search filters] + [limit, offset]
        final_params = params + [limit, offset]
        users_data = cursor.execute(query, final_params).fetchall()
        user_ids = [u["id"] for u in users_data]

        # Pobieranie gatunków w paczkach (batch)
        genres_map = {}
        if user_ids:
            placeholders = ", ".join(["?"] * len(user_ids))
            genre_query = f"""
                SELECT ufg.user_id, g.name FROM user_favorite_genres ufg
                JOIN genres g ON ufg.genre_id = g.id
                WHERE ufg.user_id IN ({placeholders})
            """
            genre_rows = cursor.execute(genre_query, user_ids).fetchall()
            for row in genre_rows:
                uid, gname = row[0], row[1]
                if uid not in genres_map:
                    genres_map[uid] = []
                genres_map[uid].append(gname)

        users = []
        now = datetime.now()

        for u in users_data:
            # Konwersja dat przy użyciu helpera
            reg_date = DateHelper.to_datetime(u["date_joined"])
            last_act = DateHelper.to_datetime(u["last_activity"])

            # Obliczanie stażu konta dla okresu globalnego
            days_since_reg = (now - reg_date).days if reg_date else 1
            days_since_reg = max(days_since_reg, 1)

            # Ustalenie dzielnika dla PPD
            if p_lower == "all":
                final_divisor = days_since_reg
            else:
                final_divisor = fixed_days if fixed_days else 1

            # Obliczanie Systematic PPD na podstawie kryteriów czasowych
            total_p = u["total_pages"] if u["total_pages"] is not None else 0
            calculated_ppd = total_p / final_divisor if final_divisor > 0 else 0.0
            db_ppd = round(calculated_ppd, 1)

            users.append(
                User(
                    id=u["id"],
                    username=u["username"],
                    name=u["name"],
                    email=u["email"],
                    status=u["status"],
                    birth_date=DateHelper.to_datetime(u["birth_date"]),
                    books_read=u["books_count"],
                    pages_per_day=db_ppd,
                    last_activity=last_act,
                    date_joined=reg_date,
                    r_tier=u["r_tier"],
                    favorite_genres=genres_map.get(u["id"], []),
                )
            )

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
            query += " WHERE (name LIKE ? OR username LIKE ? OR id LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term, term])

        cursor.execute(query, params)
        res = cursor.fetchone()
        return res[0] if res else 0

    def get_currently_reading_coverage(self, active_only: bool = False):
        """Zwraca pokrycie CURRENTLY READING: (total_users, without_reading, pct_without_reading)."""
        cursor = self.conn.cursor()
        where_active = "WHERE u.status = 'active'" if active_only else ""
        query = f"""
            WITH per_user AS (
                SELECT
                    u.id,
                    COUNT(CASE WHEN ub.status = 'reading' THEN 1 END) AS reading_count
                FROM users u
                LEFT JOIN user_books ub ON ub.user_id = u.id
                {where_active}
                GROUP BY u.id
            )
            SELECT
                COUNT(*) AS total_users,
                SUM(CASE WHEN reading_count = 0 THEN 1 ELSE 0 END) AS without_reading,
                ROUND(
                    100.0 * SUM(CASE WHEN reading_count = 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                    2
                ) AS pct_without_reading
            FROM per_user
        """
        cursor.execute(query)
        row = cursor.fetchone()
        if not row:
            return 0, 0, 0.0
        return int(row[0] or 0), int(row[1] or 0), float(row[2] or 0.0)

    def get_detailed_user_profile(self, user_id: int):
        """Pobiera profil z uwzględnieniem Potential PPD (ACTIVITY BASED) oraz streak."""
        cursor = self.conn.cursor()
        try:
            # Pobieranie aktualnie czytanych książek z limitem
            cursor.execute(
                "SELECT b.title FROM user_books ub JOIN books b ON ub.book_id = b.id WHERE ub.user_id = ? AND ub.status = 'reading' LIMIT 3",
                (user_id,),
            )
            reading_now = [r[0] for r in cursor.fetchall()]

            # Pobieranie danych bazowych użytkownika wraz z postępem wyzwań
            cursor.execute(
                """
                SELECT
                    u.external_id, u.birth_date, u.last_activity, u.date_joined,
                    u.name, u.username, u.status,
                    (SELECT SUM(pages_read) FROM activity WHERE user_id = u.id) as total_pages,
                    AVG(CAST(c.current_value AS FLOAT) / c.target_value * 100) as avg_progress
                FROM users u
                LEFT JOIN challenges c ON u.id = c.user_id AND c.status = 'active'
                WHERE u.id = ? GROUP BY u.id
            """,
                (user_id,),
            )
            u_data = cursor.fetchone()

            if not u_data:
                return None

            # Rozpakowanie pobranych danych profilowych
            (
                ext_id,
                birth_date_raw,
                last_act_raw,
                reg_date_raw,
                name,
                username,
                status,
                total_pages_sum,
                avg_progress,
            ) = u_data
            total_pages_sum = total_pages_sum or 0

            # Statystyki aktywności i wyliczanie Potential PPD na podstawie faktycznych dni czytania
            streak = self.get_user_streak(user_id)
            real_active_days = self.get_active_reading_days(user_id)
            potential_ppd = UserPerformanceService.get_potential_ppd(
                total_pages_sum or 0, real_active_days
            )

            # Obliczanie wieku użytkownika
            age = DateHelper.calculate_age(birth_date_raw)

            # Obliczanie regularności (Activity Ratio) za ostatnie 30 dni
            cursor_performance = self.conn.cursor()

            # Obsługa nowego konta zarejestrowanego dzisiaj
            reg_date_dt = DateHelper.to_datetime(reg_date_raw)
            reg_date = reg_date_dt.date() if reg_date_dt else datetime.now().date()

            if reg_date == datetime.now().date():
                consistency_score = (1.0 / 30) * 100
            else:
                active_days_30 = UserPerformanceService.get_active_days_in_range(
                    cursor_performance, user_id, 30
                )
                consistency_score = UserPerformanceService.calculate_consistency_score(
                    active_days_30, 30
                )

            return {
                "ext_id": ext_id,
                "name": name,
                "username": username,
                "status": status,
                "reading_now": reading_now,
                "total_pages": total_pages_sum,
                "avg_progress": int(avg_progress) if avg_progress else 0,
                "streak": streak,
                "potential_ppd": round(potential_ppd, 1),
                "consistency_score": round(consistency_score, 1),
                "age": age,
                "last_activity": last_act_raw,
                "date_joined": reg_date_raw,
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
        """Pobiera gotowy, przeliczony streak z bazy danych (High Performance)."""
        cursor = self.conn.cursor()
        res = cursor.execute(
            "SELECT current_streak FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return res[0] if res and res[0] else 0
    

    def get_user_report_metrics(self, period: str = "all"):
        """Pobiera metryki dla User Report - total, growth, average PPD."""
        cursor = self.conn.cursor()

        # Całkowita liczba użytkowników w systemie
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # Wyznaczanie liczby nowych użytkowników dla określonego przedziału czasowego
        since = None if period.lower() == "all" else period_start(period)
        if since:
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE date_joined >= ?", (since_str,)
            )
            new_users = cursor.fetchone()[0] or 0
        else:
            new_users = 0

        # Wyliczanie średniej wartości PPD aktywnej społeczności
        cursor.execute("SELECT AVG(pages_per_day) FROM users WHERE status = 'active'")
        avg_ppd = cursor.fetchone()[0] or 0

        return total_users, new_users, round(avg_ppd, 1)

    def get_top_users_report(self, period: str = "all", limit: int = 5):
        """Pobiera top użytkowników rankingiem - top 5 wg stron przeczytanych w okresie."""
        cursor = self.conn.cursor()

        since = None if period.lower() == "all" else period_start(period)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S") if since else None

        # Dynamiczne filtrowanie czasu dla subquery
        time_filter = "AND timestamp >= ?" if since_str else ""
        params = []
        if since_str:
            params.append(since_str)

        # Mapowanie przedziałów czasowych na dni robocze raportu
        p_lower = period.lower()
        if p_lower == "week":
            period_days = 7
        elif p_lower == "month":
            period_days = 30
        elif p_lower == "year":
            period_days = 365
        else:
            period_days = 365

        query = f"""
            SELECT
                u.id,
                u.username,
                COALESCE((SELECT SUM(pages_read) FROM activity WHERE user_id = u.id {time_filter}), 0) as pages_in_period,
                u.current_streak,
                u.date_joined
            FROM users u
            WHERE u.status = 'active'
            ORDER BY pages_in_period DESC
            LIMIT ?
        """

        final_params = params + [limit]
        rows = cursor.execute(query, final_params).fetchall()

        result = []
        for user_id, username, pages_period, streak, date_joined in rows:
            # Obliczenie współczynnika regularności użytkownika w wyznaczonym oknie czasowym
            reg_date_dt = datetime.strptime(date_joined, "%Y-%m-%d %H:%M:%S")
            reg_date = reg_date_dt.date()

            # Specjalna obsługa kont zarejestrowanych w dniu generowania zestawienia
            if reg_date == datetime.now().date():
                consistency_score = (1.0 / period_days) * 100
            else:
                active_days = UserPerformanceService.get_active_days_in_range(
                    cursor, user_id, period_days
                )
                consistency_score = UserPerformanceService.calculate_consistency_score(
                    active_days, period_days
                )

            result.append((username, pages_period, streak, round(consistency_score, 1)))

        return result