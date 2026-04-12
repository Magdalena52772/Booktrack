import random
import numpy as np
from data.config import SIM_SETTINGS
from data.config import ARCHETYPE_SETTINGS, get_fake

# ==================== FUNKCJE POMOCNICZE =====================
def calculate_session_details(arch_name, is_weekend, remaining_pages):
    """Oblicza parametry sesji na podstawie globalnych ustawień."""
    arch_cfg = ARCHETYPE_SETTINGS[arch_name]
    dp_min, dp_max = arch_cfg["pages_range"]
    
    # Parametry z SIM_SETTINGS
    w_min, w_max = SIM_SETTINGS["weekend_boost_range"]
    pace_min, pace_max = SIM_SETTINGS["page_pace_range"]
    
    multiplier = random.uniform(w_min, w_max) if is_weekend else 1.0
    
    base_pages = random.randint(dp_min, dp_max)
    pages_read = int(base_pages * multiplier)
    pages_read = max(1, min(pages_read, remaining_pages))
    
    duration = max(SIM_SETTINGS["min_session_time"], 
                   int(pages_read * random.uniform(pace_min, pace_max)))
    
    return pages_read, duration


def generate_birth_date():
    """
    Generuje realistyczną datę urodzenia.
    Wykorzystuje rozkład normalny, aby większość użytkowników była w wieku 18-45 lat.
    """
    rand = random.random()
    if rand < 0.70: 
        # Główna grupa dorosłych (rozkład wokół 32 lat)
        age = int(np.random.normal(32, 8))
        age = max(18, min(55, age))
    elif rand < 0.85:
        # Grupa seniorów
        age = random.randint(60, 80)
    else:
        # Grupa młodzieży
        age = random.randint(12, 17)

    # Zamiana wyliczonego wieku na obiekt daty przy użyciu Fakera
    return get_fake().date_of_birth(minimum_age=age, maximum_age=age)


def get_genre_map(cursor):
    """
    Pobiera mapę gatunków (name -> id) z bazy danych.
    Zamiast powtarzać tę samą query w każdym generatorze.
    """
    query = "SELECT name, id FROM genres"
    cursor.execute(query)
    return {name: gid for name, gid in cursor.fetchall()}