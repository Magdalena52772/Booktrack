"""Serwis do generacji danych symulacyjnych

Zawiera logikę biznesową dla generowania realistycznych parametrów
czytelników i sesji czytania na podstawie konfiguracji
"""

import random
import numpy as np
from data.config import SIM_SETTINGS, ARCHETYPE_SETTINGS, get_fake
from data.config import (
    GENRES,
    GENRE_WEIGHTS,
    AGE_BASED_GENRES,
    FAVORITE_GENRE_BIAS,
    READING_ANOMALY,
)
from data.utils.helpers.date_helpers import DateHelper


class GeneratorService:
    """Serwis do obsługi generacji danych dla symulacji"""

    @staticmethod
    def calculate_session_details(
        arch_name: str, is_weekend: bool, remaining_pages: int
    ) -> tuple:
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
        duration = max(
            SIM_SETTINGS["min_session_time"],
            int(pages_read * random.uniform(pace_min, pace_max)),
        )

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
            age = int(max(18, min(55, age)))
        elif rand < 0.85:
            # Grupa seniorów
            age = random.randint(60, 80)
        else:
            # Grupa młodzieży
            age = random.randint(12, 17)

        # Konwersja wyliczonego wieku na obiekt daty i formatowanie do stringa YYYY-MM-DD
        dob_date = get_fake().date_of_birth(minimum_age=age, maximum_age=age)
        return dob_date.strftime("%Y-%m-%d")

    @staticmethod
    def age_category_from_birth(birth_date) -> str:
        """Zwraca kategorię wiekową: 'junior', 'young_adult', 'adult', 'senior'"""
        if not birth_date:
            return "adult"
        bd = DateHelper.to_datetime(birth_date)
        age = DateHelper.calculate_age(bd)
        return (
            "junior"
            if age < 18
            else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        )

    @staticmethod
    def generate_favorite_genres_for_birth(birth_date):
        """Generuje listę unikalnych ulubionych gatunków z uwzględnieniem wag dla wieku"""
        cat = GeneratorService.age_category_from_birth(birth_date)
        age_genres = AGE_BASED_GENRES.get(cat, GENRES)
        
        fav_genres = set()
        fav_count = random.randint(1, 3)
        
        # Filtruje globalne wagi specjalnie pod aktualną grupę wiekową
        age_weights = []
        for g in age_genres:
            if g in GENRES:
                idx = GENRES.index(g)
                age_weights.append(GENRE_WEIGHTS[idx])
            else:
                age_weights.append(5)
        
        attempts = 0
        while len(fav_genres) < fav_count and attempts < 15:
            attempts += 1
            
            # Losuje z wagami
            if random.random() < FAVORITE_GENRE_BIAS.get("age_based_ratio", 0.9):
                picked = random.choices(age_genres, weights=age_weights, k=1)[0]
            else:
                picked = random.choices(GENRES, weights=GENRE_WEIGHTS, k=1)[0]
                
            fav_genres.add(picked)
            
        if not fav_genres:
            fav_genres.add(random.choices(GENRES, weights=GENRE_WEIGHTS, k=1)[0])
            
        return list(fav_genres)

    @staticmethod
    def generate_actual_reading_genre(birth_date, declared_genres: list):
        """Generuje gatunek rzeczywistego czytania z uwzględnieniem anomalii"""
        if not READING_ANOMALY.get("enabled", False):
            return (
                random.choice(declared_genres)
                if declared_genres
                else random.choice(GENRES)
            )

        bd = DateHelper.to_datetime(birth_date)
        age = DateHelper.calculate_age(bd)

        # Wybór profilu anomalii
        if age < 16:
            profile = READING_ANOMALY.get("junior_under_16", {})
        elif age <= 17:
            profile = READING_ANOMALY.get("junior_16_17", {})
        elif age <= 25:
            profile = READING_ANOMALY.get("young_adult", {})
        elif age <= 60:
            profile = READING_ANOMALY.get("adult", {})
        else:
            profile = READING_ANOMALY.get("senior", {})

        anomaly_ratio = profile.get("anomaly_ratio", 0.0)

        # Zastosowanie anomalii
        if random.random() < anomaly_ratio:
            swap_to = profile.get("swap_to", [])
            adult_genres = profile.get("adult_genres", [])

            if swap_to and random.random() < 0.6:
                return random.choice(swap_to)
            elif adult_genres:
                return random.choice(adult_genres)

        # Jeśli brak anomalii, wybiera z deklarowanych lub globalnych
        return (
            random.choice(declared_genres) if declared_genres else random.choice(GENRES)
        )
