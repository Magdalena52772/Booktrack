from datetime import datetime, timedelta
from data.utils.time_periods import period_start
from data.utils.time_filter_service import TimeFilterService

class StatsRepository:
    """
    Repozytorium odpowiedzialne za obliczenia statystyczne i analitykę danych.
    Zapewnia dostęp do zagregowanych wskaźników aktywności oraz raportów systemowych.
    """
    def __init__(self, conn):
        self.conn = conn

    def get_system_wide_ppd(self, period: str = "all") -> float:
        """
        Oblicza średnią liczbę stron przeczytanych dziennie przez użytkownika (PPD).
        Wykorzystuje grupowanie po identyfikatorze użytkownika i dacie dla analityki.
        """
        cursor = self.conn.cursor()

        # Centralizowana logika filtrowania czasowego
        where_clause, params = TimeFilterService.build_time_filter(period.lower())

        # Optymalizacja wydajnościowa poprzez wstępne filtrowanie danych w podzapytaniu
        query = f"""
            SELECT IFNULL(AVG(daily_sum), 0.0)
            FROM (
                SELECT SUM(pages_read) as daily_sum
                FROM activity
                {where_clause}
                GROUP BY user_id, DATE(timestamp)
            )
        """
        cursor.execute(query, params)
        res = cursor.fetchone()
        return round(float(res[0]), 1) if res else 0.0

    def get_dashboard_metrics(self):
        """
        Pobiera kluczowe metryki dla panelu głównego (Dashboard).
        Zwraca: całkowitą liczbę użytkowników, nowe konta (30 dni) oraz średnie PPD.
        """
        cursor = self.conn.cursor()
        # Definicja progu czasowego dla analizy aktywności i nowych rejestracji
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Pobieranie ogólnej liczby rekordów w tabeli użytkowników
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # Wyznaczanie liczby nowych rejestracji w ostatnim cyklu 30-dniowym
        cursor.execute("SELECT COUNT(*) FROM users WHERE date_joined >= ?", (thirty_days_ago,))
        new_users = cursor.fetchone()[0] or 0

        # Wykorzystanie zoptymalizowanej metody PPD dla zakresu miesięcznego
        avg_pages = self.get_system_wide_ppd("month")

        return total_users, new_users, avg_pages
    
    def get_user_report_metrics(self, period="year"):
        """
        Generuje dane statystyczne na potrzeby modułu raportów użytkowników.
        Analizuje liczebność bazy oraz zaangażowanie w wybranym przedziale czasowym.
        """
        cursor = self.conn.cursor()
        
        # Określenie ramy czasowej i mianownika dla średniej
        p_lower = period.lower()
        start_dt = None if p_lower == "all" else period_start(period)
        
        # Pobieranie stanu liczbowego wszystkich kont
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        # Wyznaczanie liczby kont utworzonych w zadanym okresie
        new_users = 0
        if start_dt:
            cursor.execute("SELECT COUNT(*) FROM users WHERE date_joined >= ?", 
                          (start_dt.strftime("%Y-%m-%d %H:%M:%S"),))
            new_users = cursor.fetchone()[0] or 0
        else:
            new_users = total_users

        # Obliczanie średniego PPD z uwzględnieniem przekazanego okresu
        avg_engagement = self.get_system_wide_ppd(period)

        return total_users, new_users, avg_engagement
    
    def get_report_summary(self, period="all"):
        """
        Pobiera podsumowanie aktywności w podziale na gatunki literackie.
        Identyfikuje najpopularniejszy gatunek oraz zlicza unikalne gatunki aktywne.
        """
        cursor = self.conn.cursor()
        start_dt = None if period.lower() == "all" else period_start(period)
        
        params = []
        where_clause = ""
        if start_dt:
            where_clause = "WHERE a.timestamp >= ?"
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Identyfikacja gatunku o najwyższej sumie przeczytanych stron
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
        
        # Wyznaczanie liczby gatunków, w których odnotowano jakąkolwiek aktywność
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