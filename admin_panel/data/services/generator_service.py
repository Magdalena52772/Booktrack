"""Serwis do generacji danych symulacyjnych

Zawiera logikę biznesową dla generowania realistycznych parametrów
czytelników i sesji czytania na podstawie konfiguracji
"""
import random
import numpy as np
from data.config import SIM_SETTINGS, ARCHETYPE_SETTINGS, get_fake


class GeneratorService:
    """Serwis do obsługi generacji danych dla symulacji"""

    @staticmethod
    def calculate_session_details(arch_name: str, is_weekend: bool, remaining_pages: int) -> tuple:
        """
        Oblicza parametry sesji na podstawie archetypu i warunków

        Bierze pod uwagę:
        - Typ czytelnika (casual, regular, avid, power)
        - Czy to weekend (boost do czytania)
        - Ile stron pozostało do przeczytania
        """
        arch_cfg = ARCHETYPE_SETTINGS[arch_name]
        dp_min, dp_max = arch_cfg["pages_range"]

        # Parametry z konfiguracji symulacji
        w_min, w_max = SIM_SETTINGS["weekend_boost_range"]
        pace_min, pace_max = SIM_SETTINGS["page_pace_range"]

        # Weekend boost (m. weekend_boost_range to 1.0 dla tygodnia)
        multiplier = random.uniform(w_min, w_max) if is_weekend else 1.0

        # Bazowa liczba stron z zakresu archetypu
        base_pages = random.randint(dp_min, dp_max)
        pages_read = int(base_pages * multiplier)
        # Bezpieczeństwo: nie czytamy więcej niż zostało
        pages_read = max(1, min(pages_read, remaining_pages))

        # Czas sesji: im więcej stron, tym więcej czasu
        # (randomowe tempo czytania)
        duration = max(SIM_SETTINGS["min_session_time"],
                       int(pages_read * random.uniform(pace_min, pace_max)))

        return pages_read, duration

    @staticmethod
    def generate_birth_date() -> str:
        """
        Generuje realistyczną datę urodzenia dla użytkownika.

        Rozkład:
        - 70%: Dorośli 18-45 lat (dist. normalny wokół 32 lat)
        - 15%: Seniorzy 60-80 lat
        - 15%: Młodzież 12-17 lat

        Returns:
            Data urodzenia jako string (format bazy danych)
        """
        rand = random.random()

        if rand < 0.70:
            # Główna grupa dorosłych (rozkład normalny wokół 32 lat)
            age = int(np.random.normal(32, 8))
            age = max(18, min(55, age))
        elif rand < 0.85:
            # Grupa seniorów
            age = random.randint(60, 80)
        else:
            # Grupa młodzieży
            age = random.randint(12, 17)

        # Konwersja wyliczonego wieku na obiekt daty przy użyciu Fakera
        return get_fake().date_of_birth(minimum_age=age, maximum_age=age)
