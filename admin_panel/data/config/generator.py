"""Konfiguracja generatora i symulacji danych."""

# ============== USTAWIENIA OGÓLNE ==============
USER_COUNT = 1000       # Liczba użytkowników do wygenerowania
BOOK_COUNT = 80         # Bazowa liczba książek w systemie
ACTIVITY_COUNT = 500    # Liczba dodatkowych rekordów aktywności

# ============== DEMOGRAFIA I TRENDY ==============
# Gatunki literackie i ich "waga"
GENRES = [
    "Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical fiction",
    "Crime", "Biography", "Young Adult", "Drama", "Fiction", "Childrens literature"
]

# Wagi popularności gatunków (oznaczane jako ulubione)
GENRE_WEIGHTS = [15, 15, 12, 12, 8, 8, 5, 5, 5, 10, 5]

# Rozkład wieku użytkowników (prawdopodobieństwo dla każdej grupy)
AGE_DISTRIBUTION = {
    "adult": 0.70,  # 18-55 lat
    "senior": 0.15, # 60-80 lat
    "junior": 0.15  # 12-17 lat
}

# Przypisanie gatunków do grup wiekowych
AGE_BASED_GENRES = {
    "junior": ["Childrens literature", "Fantasy", "Young Adult"],
    "young_adult": ["Young Adult", "Romance", "Drama", "Fantasy", "Sci-Fi"],
    "adult": ["Crime", "Thriller", "Fiction", "Biography", "Historical fiction"],
    "senior": ["Historical fiction", "Biography", "Crime", "Drama"]
}

# Preferencje ulubień wobec grupy wiekowej (przy generowaniu favorite_genres)
FAVORITE_GENRE_BIAS = {
    "age_based_ratio": 0.90,  # 90% ulubień z age group genres
    "random_ratio": 0.10      # 10% ulubień z globalnego rozkładu (GENRE_WEIGHTS)
}

# Anomalie między deklarowanymi a rzeczywistymi gatunkami (szum w danych)
READING_ANOMALY = {
    "enabled": True,
    "junior_under_16": {"anomaly_ratio": 0.0, "adult_genres": []},  # Brak anomalii dla <16
    "junior_16_17": {"anomaly_ratio": 0.15, "adult_genres": ["Thriller", "Crime"]},  # 15% dorosłych
    "young_adult": {"anomaly_ratio": 0.25, "swap_to": ["Thriller", "Romance", "Fiction"]},  # Declaruje Sci-Fi, czyta Thriller
    "adult": {"anomaly_ratio": 0.20, "swap_to": ["Thriller", "Crime", "Fiction"]},  # Declaruje Biography, czyta Thriller
    "senior": {"anomaly_ratio": 0.10, "swap_to": ["Childrens literature"]}  # 10% dla dziadków, którzy czytają bajki wnukom
}

# ============== AKTYWNOŚĆ ==============
INACTIVE_PROBABILITY = 0.07   # 7% użytkowników to konta porzucone
SIX_MONTHS_INACTIVITY = 180   # Po ilu dniach bezaktywności konto jest nieaktywne

# Mnożnik intensywności czytania (1: styczeń -> 12: grudzień)
# Wartości > 1.0 to wysoki sezon (więcej czytania)
# Zima/Jesień > 1.0, Lato < 1.0
SEASONAL_IMPACT = {
    1: 1.6, 2: 1.5, 3: 1.1, 4: 0.8, 5: 0.7, 6: 0.6,
    7: 0.8, 8: 0.9, 9: 1.1, 10: 1.3, 11: 1.5, 12: 1.7
}

# ============== OCENY I RECENZJE ==============
RATING_SETTINGS = {
    "review_probability": 0.85,          # 85% szans że użytkownik oceni skończoną książkę
    "scores": [1, 2, 3, 4, 5],           # Dostępne oceny
    "weights": [2, 5, 15, 45, 33]        # Rozkład: głównie 4 (45%) i 5 (33%)
}

# ============== USTAWIENIA SYMULACJI ==============
SIM_SETTINGS = {
    "weekend_boost_range": (1.3, 1.8),  # Losowy mnożnik dla sesji weekendowych
    "page_pace_range": (0.8, 1.5),      # Ile minut na jedną stronę
    "min_session_time": 5,               # Minimalny czas sesji w minutach
    "gap_power_user": [1, 1, 1, 2],     # Przerwy (dni) dla archetypu 'power'
    "gap_standard": (1, 4)               # Przerwy (dni) dla pozostałych archetypów
}

# ============== ARCHETYPY CZYTELNIKÓW ==============
# Konfiguracja limitów dla poszczególnych archetypów
ARCHETYPE_SETTINGS = {
    "casual":  {"pages_range": (5, 15),  "annual_limit": (1, 6), "chance": 0.25},   # Czytelnik okazjonalny
    "regular": {"pages_range": (15, 25), "annual_limit": (7, 15), "chance": 0.50},  # Czytelnik zwykły
    "avid":    {"pages_range": (25, 45), "annual_limit": (16, 35), "chance": 0.75}, # Zapalony czytelnik
    "power":   {"pages_range": (40, 70), "annual_limit": (36, 65), "chance": 1.00}  # Superczytelnik
}

# ============== WYZWANIA CZYTELNICZE ==============
CHALLENGE_SETTINGS = {
    "count_per_user": 3,
    "target_range": (5, 52),      # Ile książek do przeczytania w wyzwaniu
    "duration_days": (30, 365),   # Czas trwania wyzwania (dni)
}
