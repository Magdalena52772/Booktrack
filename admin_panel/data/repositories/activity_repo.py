import sqlite3
from data.services.time_filter_service import TimeFilterService

class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_activity_kpi(self, time_filter="week"):
        """
        Pobieranie wskaźników KPI z uwzględnieniem uśrednionej aktywności dziennej.
        Zwraca: total_pages, user_retention (%), avg_per_day
        """
        cursor = self.conn.cursor()

        # Centralizowana logika filtrowania czasowego
        condition, params = TimeFilterService.build_time_filter(time_filter)
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        # Obliczanie sumy stron
        cursor.execute(f"SELECT IFNULL(SUM(pages_read), 0) FROM activity {where_clause}", params)
        total_pages = cursor.fetchone()[0]

        # Obliczanie rzeczywistej retencji: % użytkowników aktywnych w okresie
        user_retention = self.get_user_retention(time_filter)

        # Wyliczanie średniej dziennej na użytkownika
        avg_query = f"""
            SELECT IFNULL(AVG(daily_total), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_total
                FROM activity
                {where_clause}
                GROUP BY user_id, SUBSTR(timestamp, 1, 10)
            )
        """
        cursor.execute(avg_query, params)
        avg_per_day = cursor.fetchone()[0]

        # Zwrot przetworzonych wskaźników z zaokrągleniem wartości średniej
        return int(total_pages), user_retention, round(float(avg_per_day), 1)

    def get_user_retention(self, time_filter="week"):
        """
        Oblicza % użytkowników którzy byli aktywni w wybranym okresie.
        For non-'all' periods (week/month/year) retention is computed as
        the share of users active in the previous comparable period who
        remained active in the current period (period-to-period retention).
        For 'all' we fall back to active_users / total_active_users as before.
        """
        cursor = self.conn.cursor()
        p_lower = time_filter.lower()

        # For 'all' behave like before: active users in activity / total active users
        if p_lower == "all":
            # Pobieranie total users
            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
            total_users = cursor.fetchone()[0] or 0

            # unique active users in activity period (join to users to ensure existence)
            condition, params = TimeFilterService.build_time_filter(time_filter)
            where_clause = f"WHERE 1=1 {condition}" if condition else ""
            query = f"SELECT COUNT(DISTINCT a.user_id) FROM activity a JOIN users u ON a.user_id = u.id AND u.status = 'active' {where_clause}"
            cursor.execute(query, params)
            active_users = cursor.fetchone()[0] or 0

            if total_users == 0:
                return 0.0

            retention = (active_users / total_users) * 100
            retention = max(0.0, min(100.0, retention))
            return round(retention, 1)

        # For periodic retention compute period-to-period retention:
        # retention = (users_active_current_period ∩ users_active_previous_period) / users_active_previous_period
        from data.utils.time_periods import period_start
        from datetime import datetime, timedelta

        since_current = period_start(p_lower)
        # Number of days in period (approximate for week/month/year)
        period_days = (datetime.now() - since_current).days or 1
        since_prev = since_current - timedelta(days=period_days)

        since_prev_str = since_prev.strftime("%Y-%m-%d %H:%M:%S")
        since_curr_str = since_current.strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Users active in previous period
        q_prev = "SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp < ?"
        cursor.execute(q_prev, (since_prev_str, since_curr_str))
        prev_rows = cursor.fetchall()
        prev_users = set(r[0] for r in prev_rows)
        prev_count = len(prev_users)

        if prev_count == 0:
            return 0.0

        # Users active in current period
        q_curr = "SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp <= ?"
        cursor.execute(q_curr, (since_curr_str, now_str))
        curr_rows = cursor.fetchall()
        curr_users = set(r[0] for r in curr_rows)

        retained = len(prev_users.intersection(curr_users))
        retention = (retained / prev_count) * 100.0
        retention = max(0.0, min(100.0, retention))
        return round(retention, 1)

    def get_activity_kpi_core(self, time_filter="week"):
        """
        Pobieranie total_pages i active_days. Używane przez ActivityView
        """
        cursor = self.conn.cursor()

        # Centralizowana logika filtrowania czasowego
        condition, params = TimeFilterService.build_time_filter(time_filter)
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        # Obliczanie sumy stron
        cursor.execute(f"SELECT IFNULL(SUM(pages_read), 0) FROM activity {where_clause}", params)
        total_pages = cursor.fetchone()[0]

        # Wyznaczanie liczby unikalnych dni
        cursor.execute(f"SELECT COUNT(DISTINCT DATE(timestamp)) FROM activity {where_clause}", params)
        active_days = cursor.fetchone()[0] or 0

        return int(total_pages), active_days


    def get_activity_trend(self, time_filter="week"):
        """Pobieranie trendu aktywności"""
        cursor = self.conn.cursor()
        f_type = time_filter.lower()

        if f_type == "week":
            # Week: RECURSIVE CTE (7 dni)
            query = """
                WITH RECURSIVE calendar(d) AS (
                    SELECT date('now', '-6 days')
                    UNION ALL
                    SELECT date(d, '+1 day') FROM calendar WHERE d < date('now')
                )
                SELECT c.d, IFNULL(SUM(a.pages_read), 0)
                FROM calendar c
                LEFT JOIN activity a ON a.timestamp >= c.d || ' 00:00:00'
                                    AND a.timestamp <= c.d || ' 23:59:59'
                GROUP BY c.d
                ORDER BY c.d ASC
            """
            cursor.execute(query)
        elif f_type == "month":
            # Month: GROUP BY
            query = """
                SELECT DATE(timestamp), IFNULL(SUM(pages_read), 0)
                FROM activity
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp) ASC
            """
            cursor.execute(query)
        elif f_type == "year":
            # Year: Agreguje po tygodniach (52 punkty)
            query = """
                SELECT
                    DATE(timestamp, 'weekday 0', '-6 days') as week_start,
                    SUM(pages_read) as total
                FROM activity
                WHERE timestamp >= date('now', '-364 days')
                GROUP BY DATE(timestamp, 'weekday 0', '-6 days')
                ORDER BY week_start ASC
            """
            cursor.execute(query)
        else:
            # "all" - ostatnie 24 miesiące
            query = """
                SELECT STRFTIME('%Y-%m', timestamp) as period, SUM(pages_read)
                FROM activity
                WHERE timestamp > date('now', '-24 months')
                GROUP BY period
                ORDER BY period ASC
            """
            cursor.execute(query)

        results = cursor.fetchall()
        return results if results else []
    
    def get_unique_active_users(self, time_filter="all"):
        """Zwraca liczbę unikalnych użytkowników, którzy byli aktywni w danym okresie."""
        cursor = self.conn.cursor()

        # Centralizowana logika filtrowania czasowego
        condition, params = TimeFilterService.build_time_filter(time_filter)
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        query = f"SELECT COUNT(DISTINCT user_id) FROM activity {where_clause}"
        cursor.execute(query, params)
        res = cursor.fetchone()
        return res[0] if res else 0

    def get_peak_activity(self, trend_data):
        """Znajduje najwyższy punkt w trendzie i zwraca wartość oraz sformatowaną datę"""
        if not trend_data:
            return 0, "N/A"

        # trend_data - krotka (data, suma_stron)
        max_entry = max(trend_data, key=lambda x: x[1])
        raw_date = max_entry[0]
        peak_val = max_entry[1]

        return peak_val

    def get_recent_activity_logs(self, limit=50):
        """
        Pobiera ostatnie X logów aktywności z formatowaniem dla LiveFeed.
        Zwraca listę tuples: (timestamp_str, formatted_message)
        Np: ("16:03:33", "📖 User123 read 25 pages of 'Harry Potter'")
        """
        cursor = self.conn.cursor()

        query = """
            SELECT
                a.timestamp,
                u.username,
                b.title,
                a.pages_read
            FROM activity a
            JOIN users u ON a.user_id = u.id
            JOIN books b ON a.book_id = b.id
            ORDER BY a.timestamp DESC
            LIMIT ?
        """

        cursor.execute(query, (limit,))
        results = cursor.fetchall()

        # Formatowanie wyników
        formatted_logs = []
        for timestamp, username, title, pages in reversed(results):  # Reverse dla chronologicznego porządku
            # Ekstraktuje czas z timestamp
            time_str = timestamp.split(" ")[1][:8] if " " in timestamp else "??:??:??"

            # Sformatuje wiadomość ze statusem czytania
            message = f"📖 {username} read {pages} pages of '{title}'"

            formatted_logs.append((time_str, message))

        return formatted_logs

    def get_trend_analysis(self, time_filter="week"):
        """Pobiera dane trendu z analizą porównawczą okresu.
        Zwraca: trend_current, trend_previous, growth_percent, peak_value
        """
        from data.utils.time_periods import period_start
        from datetime import datetime, timedelta

        cursor = self.conn.cursor()

        # Aktualne dane trendu
        current_trend = self.get_activity_trend(time_filter)

        if not current_trend or len(current_trend) == 0:
            return [], 0, 0.0, 0

        # Obliczanie summy stron w okresie
        current_sum = sum(row[1] for row in current_trend)

        # Wyliczanie wzrostu w porównaniu z poprzednim okresem (jeśli nie "all")
        growth_percent = 0.0
        if time_filter.lower() != "all":
            # Pobieranie poprzedniego okresu
            since_current = period_start(time_filter)
            period_days = (datetime.now() - since_current).days
            since_previous = since_current - timedelta(days=period_days)

            since_prev_str = since_previous.strftime("%Y-%m-%d %H:%M:%S")
            since_curr_str = since_current.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "SELECT IFNULL(SUM(pages_read), 0) FROM activity WHERE timestamp >= ? AND timestamp < ?",
                (since_prev_str, since_curr_str)
            )
            previous_sum = cursor.fetchone()[0]

            if previous_sum > 0:
                growth_percent = ((current_sum - previous_sum) / previous_sum) * 100

        # Znajdowanie piku
        peak_value = self.get_peak_activity(current_trend)

        return current_trend, current_sum, round(growth_percent, 1), peak_value

    def get_user_churn(self, time_filter="week"):
        """
        Oblicza % użytkowników, którzy byli aktywni w poprzednim okresie,
        a obecnie mają status != 'active' (przeszli w inactive) — czyli churn.
        Churn = (previous_active_users_now_inactive / previous_active_users) * 100
        """
        cursor = self.conn.cursor()
        p_lower = time_filter.lower()

        if p_lower == "all":
            # For 'all' churn isn't well-defined; return 0.0
            return 0.0

        from data.utils.time_periods import period_start
        from datetime import datetime, timedelta

        since_current = period_start(p_lower)
        period_days = (datetime.now() - since_current).days or 1
        since_prev = since_current - timedelta(days=period_days)

        since_prev_str = since_prev.strftime("%Y-%m-%d %H:%M:%S")
        since_curr_str = since_current.strftime("%Y-%m-%d %H:%M:%S")

        # Users active in previous period
        q_prev = "SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp < ?"
        cursor.execute(q_prev, (since_prev_str, since_curr_str))
        prev_rows = cursor.fetchall()
        prev_users = [r[0] for r in prev_rows]
        prev_count = len(prev_users)

        if prev_count == 0:
            return 0.0

        # Count how many of those users now have status != 'active'
        placeholders = ','.join(['?'] * prev_count)
        q_inactive = f"SELECT COUNT(*) FROM users WHERE id IN ({placeholders}) AND status != 'active'"
        cursor.execute(q_inactive, prev_users)
        now_inactive = cursor.fetchone()[0] or 0

        churn = (now_inactive / prev_count) * 100.0
        churn = max(0.0, min(100.0, churn))
        return round(churn, 1)

    def get_retention_details(self, time_filter="week"):
        """
        Returns detailed retention metrics: (prev_count, retained_count, now_inactive_count, churn_pct).
        For 'all' returns (0, 0, 0, 0.0) as period-to-period metrics are not applicable.
        """
        cursor = self.conn.cursor()
        p_lower = time_filter.lower()

        if p_lower == "all":
            return 0, 0, 0, 0.0

        from data.utils.time_periods import period_start
        from datetime import datetime, timedelta

        since_current = period_start(p_lower)
        period_days = (datetime.now() - since_current).days or 1
        since_prev = since_current - timedelta(days=period_days)

        since_prev_str = since_prev.strftime("%Y-%m-%d %H:%M:%S")
        since_curr_str = since_current.strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Users active in previous period
        q_prev = "SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp < ?"
        cursor.execute(q_prev, (since_prev_str, since_curr_str))
        prev_rows = cursor.fetchall()
        prev_users = [r[0] for r in prev_rows]
        prev_count = len(prev_users)

        if prev_count == 0:
            return 0, 0, 0, 0.0

        # Users active in current period
        q_curr = "SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp <= ?"
        cursor.execute(q_curr, (since_curr_str, now_str))
        curr_rows = cursor.fetchall()
        curr_users = set(r[0] for r in curr_rows)

        retained_count = len([u for u in prev_users if u in curr_users])

        # Count how many of prev users now have status != 'active'
        placeholders = ','.join(['?'] * prev_count)
        q_inactive = f"SELECT COUNT(*) FROM users WHERE id IN ({placeholders}) AND status != 'active'"
        cursor.execute(q_inactive, prev_users)
        now_inactive = cursor.fetchone()[0] or 0

        churn = (now_inactive / prev_count) * 100.0 if prev_count > 0 else 0.0
        churn = max(0.0, min(100.0, round(churn, 1)))

        return prev_count, retained_count, now_inactive, churn