"""Konfiguracje dla panelu administracyjnego
    Zawiera kluczowe ustawienia i stałe używane w całym projekcie,
    podzielone na sekcje:
- database: Ścieżki do bazy i hasło Django
- generator: Ustawienia symulacji i generacji danych
- seed: SEED i inicjalizacja Fakera
"""

# Konfiguracja bazy danych
from .database import BASE_DIR, DB_PATH, SCHEMA_PATH, DJANGO_HASHED_PWD

# Konfiguracja generatora
from .generator import (
    USER_COUNT,
    BOOK_COUNT,
    ACTIVITY_COUNT,
    GENRES,
    GENRE_WEIGHTS,
    AGE_DISTRIBUTION,
    AGE_BASED_GENRES,
    FAVORITE_GENRE_BIAS,
    READING_ANOMALY,
    INACTIVE_PROBABILITY,
    SIX_MONTHS_INACTIVITY,
    SEASONAL_IMPACT,
    RATING_SETTINGS,
    SIM_SETTINGS,
    ARCHETYPE_SETTINGS,
    CHALLENGE_SETTINGS,
)

# Konfiguracja seeda
from .seed import SEED, get_fake

__all__ = [
    # Baza danych
    "BASE_DIR",
    "DB_PATH",
    "SCHEMA_PATH",
    "DJANGO_HASHED_PWD",
    # Generator
    "USER_COUNT",
    "BOOK_COUNT",
    "ACTIVITY_COUNT",
    "GENRES",
    "GENRE_WEIGHTS",
    "AGE_DISTRIBUTION",
    "AGE_BASED_GENRES",
    "FAVORITE_GENRE_BIAS",
    "READING_ANOMALY",
    "INACTIVE_PROBABILITY",
    "SIX_MONTHS_INACTIVITY",
    "SEASONAL_IMPACT",
    "RATING_SETTINGS",
    "SIM_SETTINGS",
    "ARCHETYPE_SETTINGS",
    "CHALLENGE_SETTINGS",
    # Seed
    "SEED",
    "get_fake",
]
