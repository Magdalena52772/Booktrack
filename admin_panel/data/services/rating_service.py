"""Serwis do obsługi logiki ocen i kolorowania

Zawiera reguły biznesowe dla mapowania ocen na kolory dla UI
"""

class RatingService:
    """Serwis do obliczania i formatowania ocen"""

    @staticmethod
    def get_rating_color(rating: float) -> str:
        """
        Zwraca kolor UI (heksadecymalny) na podstawie wartości oceny.

        Reguły:
        - >= 4.5: Ciemnozielony (#27ae60) - doskonały
        - >= 3.0: Standardowy (#2c3e50) - dobry
        - < 3.0: Pomarańczowy (#e67e22) - słaby
        """
        if rating >= 4.5:
            return "#27ae60"  # Ciemnozielony
        if rating >= 3.0:
            return "#2c3e50"  # Standardowy
        return "#e67e22"  # Pomarańczowy dla słabych ocen
