import sys
import random
from pathlib import Path
from faker import Faker

# ================= PATH FIX =================
# Umożliwia import modułów z katalogu nadrzędnego
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR.parent))
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "data"))


# ============== POWTARZALNOŚĆ SYMULACJI (SEED) ==============
# Zapewnia powtarzalność wyników
fake = Faker("pl_PL") # generuje polskich użytkowników
SEED = 52772
random.seed(SEED)
fake.seed_instance(SEED)

# =================================================================
# =================== PARAMETRY SYMULACJI =========================
# =================================================================


# --- USTAWIENIA OGÓLNE ---
USER_COUNT = 1000       # Ilu użytkowników stworzyć
BOOK_COUNT = 80         # Bazowa liczba książek w systemie
ACTIVITY_COUNT = 500    # Liczba dodatkowych aktywności

# --- DEMOGRAFIA I TRENDY ---
# Gatunki literackie i ich "waga"
GENRES = [
    "Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical fiction",
    "Crime", "Biography", "Young Adult", "Drama", "Fiction", "Childrens literature"
]

# Wagi popularności gatunków (oznaczone jako ulubione)
GENRE_WEIGHTS = [15, 15, 12, 12, 8, 8, 5, 5, 5, 10, 5]

# Rozkład wieku użytkowników (szanse na daną grupę)
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

# --- AKTYWNOŚĆ ---
INACTIVE_PROBABILITY = 0.07   # 7% użytkowników to konta porzucone
SIX_MONTHS_INACTIVITY = 180 # Po ilu dniach bezruchu konto jest uznane za nieaktywne

# Mnożnik intensywności czytania (1: Styczeń -> 12: Grudzień)
# Wartości > 1.0 oznaczają sezon wysoki (więcej czytania)
# Zima/Jesień > 1.0, Lato < 1.0
SEASONAL_IMPACT = {
    1: 1.6, 2: 1.5, 3: 1.1, 4: 0.8, 5: 0.7, 6: 0.6,
    7: 0.8, 8: 0.9, 9: 1.1, 10: 1.3, 11: 1.5, 12: 1.7
}

# --- OCENY (RATING) ---
RATING_SETTINGS = {
    "review_probability": 0.85,          # 85% szans, że użytkownik oceni skończoną książkę
    "scores": [1, 2, 3, 4, 5],           # Dostępne oceny
    "weights": [2, 5, 15, 45, 33]        # Rozkład: najwięcej 4 (45%) i 5 (33%)
}

SIM_SETTINGS = {
    "weekend_boost_range": (1.3, 1.8), # Losowy mnożnik dla sesji weekendowych
    "page_pace_range": (0.8, 1.5),     # Ile minut na 1 stronę
    "min_session_time": 5,             # Minimalny czas trwania sesji w minutach
    "gap_power_user": [1, 1, 1, 2],    # Przerwy w dniach dla archetypu 'power'
    "gap_standard": (1, 4)             # Przerwy w dniach dla pozostałych
}

# --- ARCHETYPY CZYTELNIKÓW ---
# Konfiguracja limitów dla archetypów i progi prawdopodobieństwa dla typów czytelników
ARCHETYPE_SETTINGS = {
    "casual":  {"pages_range": (5, 15),  "annual_limit": (1, 6), "chance": 0.25},   # Czytelnik, który czyta rzadko
    "regular": {"pages_range": (15, 25), "annual_limit": (7, 15), "chance": 0.50}, # Przeciętny
    "avid":    {"pages_range": (25, 45), "annual_limit": (16, 35), "chance": 0.75}, # Mole książkowe
    "power":   {"pages_range": (40, 70), "annual_limit": (36, 65), "chance": 1.00}  # Wyjątkowo zaangażowani czytelnicy
}

# --- WYZWANIA ---
CHALLENGE_SETTINGS = {
    "count_per_user": 3,
    "target_range": (5, 52),      # Ile książek do przeczytania w wyzwaniu
    "duration_days": (30, 365),    # Czas trwania wyzwania
}

# --- TECHNICZNE ---
# Zahashowane hasło 'test1234'
DJANGO_HASHED_PWD = 'pbkdf2_sha256$600000$u79vV3WpXzQ9$8p0/m/H7u0YvXmS7D5/V6eQzX7P8R9a0b1c2d3e4f5g='

# Ścieżka do bazy danych
DB_PATH = BASE_DIR / "booktrack.db"
# =============================================================