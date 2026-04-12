"""Serwis z logiką dla profili użytkowników

Zawiera kalkulacje i logikę biznesową związaną z wydajnością czytelnika
"""

class UserPerformanceService:
    """Serwis do obliczania wskaźników wydajności użytkownika"""

    @staticmethod
    def calculate_performance_status(user_ppd: float, system_avg: float) -> dict:
        """
        Oblicza status wydajności użytkownika na podstawie
        porównania ze średnią systemową (PPD - Pages Per Day)
        """
        diff = user_ppd - system_avg

        if diff > 1.0:
            status = "<b style='color: #27ae60;'>▲ ABOVE AVG</b>"
            color = "#27ae60"
        elif diff < -1.0:
            status = "<b style='color: #e67e22;'>▼ BELOW AVG</b>"
            color = "#e67e22"
        else:
            status = "<b style='color: #3498db;'>≈ ON PAR</b>"
            color = "#3498db"

        return {
            "status": status,
            "color": color,
            "diff": diff
        }

    @staticmethod
    def format_streak_display(streak: int) -> dict:
        """
        Formatuje wyświetlanie streak'a użytkownika
        """
        streak_text = f"🔥 {streak} DAYS" if streak > 0 else "❄️ NO STREAK"
        streak_color = "#e67e22" if streak > 0 else "#95a5a6"

        return {
            "text": streak_text,
            "color": streak_color
        }

    @staticmethod
    def calculate_consistency_score(active_days: int, total_days: int = 30) -> float:
        """
        Oblicza wskaźnik konsekwencji/regularności użytkownika (0-100%).

        Logika: Ile dni z aktywnością na przestrzeni ostatnich N dni.
        (np. 15 dni aktywności z 30 = 50%)
        """
        if total_days <= 0:
            return 0.0

        score = (active_days / total_days) * 100
        return round(score, 1)

    @staticmethod
    def get_active_days_in_range(cursor, user_id: int, days_limit: int) -> int:
        """
        Pobiera liczbę unikalnych dni aktywności w danym przedziale czasowym
        Pomocnicza metoda do obliczania consistency score
        """
        res = cursor.execute("""
            SELECT COUNT(DISTINCT date(timestamp))
            FROM activity
            WHERE user_id = ? AND timestamp >= date('now', ?)
        """, (user_id, f"-{days_limit} days")).fetchone()
        return res[0] if res else 0

    @staticmethod
    def get_potential_ppd(total_pages: float, active_reading_days: int) -> float:
        """
        Oblicza Potential PPD (Activity-based Pages Per Day)
        Wskaźnik wydajności tylko dla dni, w których faktycznie była aktywność
        Odzwierciedla prawdziwą moc przerobową użytkownika 
        (ignoruje dni bez aktywności)
        """
        if active_reading_days <= 0:
            return 0.0
        return round(total_pages / active_reading_days, 1)

    @staticmethod
    def calculate_all_metrics(profile_data: dict) -> dict:
        """
        Metoda łącząca wszystkie metryki wydajności w jednym miejscu 
        (SSOT dla wydajności użytkownika).

        Łączy: consistency_score, potential_ppd, performance_status
        """
        consistency = UserPerformanceService.calculate_consistency_score(
            profile_data.get("active_days_30", 0),
            total_days=30
        )

        potential_ppd = UserPerformanceService.get_potential_ppd(
            profile_data.get("total_pages", 0),
            profile_data.get("active_reading_days", 1)
        )

        performance_status = UserPerformanceService.calculate_performance_status(
            profile_data.get("user_ppd", 0.0),
            profile_data.get("system_avg", 0.0)
        )

        return {
            "consistency_score": consistency,
            "potential_ppd": potential_ppd,
            "performance_status": performance_status
        }