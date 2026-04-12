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