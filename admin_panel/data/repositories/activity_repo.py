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
        Retention = (unique active users / total users) * 100
        """
        cursor = self.conn.cursor()

        # Pobieranie total users
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        total_users = cursor.fetchone()[0] or 1

        # Pobieranie unique active users w okresie
        condition, params = TimeFilterService.build_time_filter(time_filter)
        where_clause = f"WHERE 1=1 {condition}" if condition else ""

        query = f"SELECT COUNT(DISTINCT user_id) FROM activity {where_clause}"
        cursor.execute(query, params)
        active_users = cursor.fetchone()[0] or 0

        # Obliczanie procentu
        retention = (active_users / total_users) * 100 if total_users > 0 else 0
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