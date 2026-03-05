import random
from datetime import datetime, timedelta
from faker import Faker
import sys
from pathlib import Path
import numpy as np

# ================= PATH FIX =================
# Umożliwia import modułów z katalogu nadrzędnego
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR.parent))
from data.database import get_connection

# ============== POWTARZALNOŚĆ SYMULACJI (SEED) ==============
# Zapewnia powtarzalność wyników
fake = Faker("pl_PL") # generuje polskich użytkowników
SEED = 52772
random.seed(SEED)
fake.seed_instance(SEED)

# =================================================================
# ================= PARAMETRY SYMULACJI ====================
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

# Wagi popularności gatunków (wpływają na 'Ulubione')
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

# =============================================================


# ==================== FUNKCJE POMOCNICZE =====================
def slugify(text):
    """Zamienia polskie znaki na łacińskie (np. ą -> a) dla maili i loginów."""
    mapping = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    return text.translate(mapping).lower().replace(" ", "")


def get_archetype_name(roll=None):
    """Zwraca nazwę archetypu na podstawie rzutu."""
    val = roll if roll is not None else random.random()
    for name, cfg in ARCHETYPE_SETTINGS.items():
        if val <= cfg["chance"]:
            return name
    return "regular"

def get_user_identity(index=None):
    """Generuje spójne dane tożsamości."""
    first_name = fake.first_name()
    last_name = fake.last_name()
    # Używa indexu dla masowego generowania lub random dla realtime
    suffix = index if index is not None else random.randint(100, 9999)
    
    nickname = f"{slugify(first_name + last_name)}_{suffix}"
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "nickname": nickname,
        "email": f"{nickname}@{fake.free_email_domain()}"
    }

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
    return fake.date_of_birth(minimum_age=age, maximum_age=age)


# =============== GENEROWANIE UŻYTKOWNIKÓW ===================
def generate_users(conn, count=1000):
    """Tworzy bazową tabelę użytkowników wraz z ich profilami czytelniczymi."""
    cursor = conn.cursor()
    now = datetime.now()
    
    # --- PRZYGOTOWANIE BAZY ---
    for g in GENRES:
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (g,))
    conn.commit()

    # Pobieranie mapy (id -> name)
    cursor.execute("SELECT name, id FROM genres")
    genre_map = {name: gid for name, gid in cursor.fetchall()}

    # Logika statusów
    num_inactive = int(count * INACTIVE_PROBABILITY)
    statuses = ["inactive"] * num_inactive + ["active"] * (count - num_inactive)
    random.shuffle(statuses)

    temp_users_data = [] 
    
    for i in range(count):
        # Podstawowe dane
        first_name = fake.first_name()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        nickname = f"{slugify(first_name + last_name)}_{i}" 
        email = f"{nickname}@{fake.free_email_domain()}"
        ext_id = 100000 + i
        status = statuses[i]
        
        register_date = fake.date_time_between(start_date='-2y', end_date='now')
        days_on_platform = (now - register_date).days
        account_years = max(0.1, days_on_platform / 365.25)
        
        # --- LOGIKA ARCHETYPÓW ---
        # Losuje bazowy archetyp, żeby mieć dostęp do parametrów
        r_tier_roll = random.random()
        if r_tier_roll < ARCHETYPE_SETTINGS["casual"]["chance"]: arch_name = "casual"
        elif r_tier_roll < ARCHETYPE_SETTINGS["regular"]["chance"]: arch_name = "regular"
        elif r_tier_roll < ARCHETYPE_SETTINGS["avid"]["chance"]: arch_name = "avid"
        else: arch_name = "power"
        
        # Pobieranie ustawień
        arch_cfg = ARCHETYPE_SETTINGS[arch_name]
        dp_min, dp_max = arch_cfg["pages_range"]
        annual_limit_tuple = arch_cfg["annual_limit"]
        annual_limit = random.randint(*annual_limit_tuple)

        # --- LOGIKA BIBLIOTEKI UŻYTKOWNIKA ---
        if status == "inactive":
            pages_per_day = 0.0
            reader_type = "casual"
            
            if days_on_platform > SIX_MONTHS_INACTIVITY:
                last_activity = fake.date_time_between(
                    start_date=register_date, 
                    end_date=now - timedelta(days=SIX_MONTHS_INACTIVITY)
                )
                active_days = max(1, (last_activity - register_date).days)
                active_years = active_days / 365.25
                
                # Losowanie dla nieaktywnych
                r_tier_sub = random.uniform(0, 0.5) 
                if r_tier_sub < 0.25:
                    reader_type = "casual"
                    annual_limit = random.randint(3, 8)
                else:
                    reader_type = "regular"
                    annual_limit = random.randint(9, 15)
                
                books_read = max(1, int(active_years * annual_limit))
            else:
                # Konto zbyt młode na bycie nieaktywnym - wymusza aktywność
                status = "active"
                last_activity = now
                reader_type = arch_name # zostaje przy wylosowanym wcześniej
                books_read = max(1, int(account_years * annual_limit))
                pages_per_day = round(random.uniform(dp_min, dp_max), 1)
        
        if status == "active":
            activity_start_limit = max(register_date, now - timedelta(days=7))
            last_activity = fake.date_time_between(start_date=activity_start_limit, end_date='now')
            
            # Ponowne losowanie archetypu
            r_tier_act = random.random()
            if r_tier_act < 0.25: reader_type = "casual"
            elif r_tier_act < 0.50: reader_type = "regular"
            elif r_tier_act < 0.75: reader_type = "avid"
            else: reader_type = "power"

            # Odświeża limity dla nowego reader_type
            new_cfg = ARCHETYPE_SETTINGS[reader_type]
            ann_min, ann_max = new_cfg["annual_limit"]
            dpm_min, dpm_max = new_cfg["pages_range"]
            
            books_read = max(1, int(account_years * random.randint(ann_min, ann_max)))
            pages_per_day = round(random.uniform(dpm_min, dpm_max), 1)

        birth_date_obj = generate_birth_date()
        
        # Zapis do listy
        temp_users_data.append({
            "db_tuple": (
                nickname, email, full_name, 
                register_date.strftime("%Y-%m-%d %H:%M:%S"),
                status, birth_date_obj.strftime("%Y-%m-%d"),
                ext_id, last_activity.strftime("%Y-%m-%d %H:%M:%S"),
                pages_per_day, books_read, DJANGO_HASHED_PWD,
                1, 0, 0
            ),
            "fav_genres": list(set(random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1,3)))),
            "meta": {
                "id": None,
                "r_tier": reader_type, 
                "name": nickname, 
                "date_joined": register_date, 
                "status": status, 
                "books_read": books_read,
                "birth_date": birth_date_obj,
                "last_activity": last_activity 
            }
        })

    # Sortowanie i wstawianie
    temp_users_data.sort(key=lambda u: u['meta']['date_joined'])
    cursor.executemany("""
        INSERT INTO users (
            username, email, name, date_joined, status, birth_date,
            external_id, last_activity, pages_per_day, books_read, 
            password, is_active, is_staff, is_superuser
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [u['db_tuple'] for u in temp_users_data])

    # Pobieranie ID i gatunki
    cursor.execute("SELECT id, username FROM users")
    db_users = {username: uid for uid, username in cursor.fetchall()}
    favorite_genres_tuples = []
    final_meta = []

    for u in temp_users_data:
        u_name = u['meta']['name']
        user_id = db_users.get(u_name)
        if user_id:
            u['meta']['id'] = user_id
            final_meta.append(u['meta'])
            for g_name in u['fav_genres']:
                g_id = genre_map.get(g_name)
                if g_id: favorite_genres_tuples.append((user_id, g_id))

    cursor.executemany("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", favorite_genres_tuples)
    conn.commit()
    return final_meta


# ========== GENEROWANIE NOWYCH UŻYTKOWNIKÓW ===========
def generate_realtime_user(conn):
    """
    Symuluje rejestrację nowego użytkownika w czasie rzeczywistym.
    Zapewnia spójność danych i korzysta ze zdefiniowanych archetypów.
    """
    cursor = conn.cursor()
    now = datetime.now()
    
    # Spójna tożsamość (z funkcji pomocniczej)
    identity = get_user_identity()
    nickname = identity["nickname"]
    full_name = identity["full_name"]
    
    # Weryfikacja unikalności username (zabezpieczenie przed kolizją w czasie rzeczywistym)
    while cursor.execute("SELECT 1 FROM users WHERE username = ?", (nickname,)).fetchone():
        nickname = f"{identity['nickname']}_{random.randint(100, 999)}"
    
    email = f"{nickname}@{fake.free_email_domain()}"

    # Logika Archetypu (parametry z ARCHETYPE_SETTINGS)
    arch_name = get_archetype_name()
    arch_cfg = ARCHETYPE_SETTINGS[arch_name]
    
    # Pobiera zakresy stron i limitów rocznych z konfiguracji
    dpm_min, dpm_max = arch_cfg["pages_range"]
    pages_per_day = round(random.uniform(dpm_min, dpm_max), 1)
    
    # Nowy użytkownik zaczyna z małym dorobkiem (np. 1-2 książki)
    books_read_count = random.randint(1, 2)
    
    # Pozostałe dane
    birth_date = generate_birth_date()
    register_date = now - timedelta(minutes=random.randint(5, 60))
    
    # Generowanie unikalnego external_id
    while True:
        external_id = random.randint(100000, 999999)
        if not cursor.execute("SELECT 1 FROM users WHERE external_id = ?", (external_id,)).fetchone():
            break

    # Zapis do bazy
    cursor.execute("""
        INSERT INTO users (
            username, email, name, date_joined, status, birth_date, 
            external_id, last_activity, pages_per_day, books_read, 
            password, is_active, is_staff, is_superuser
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nickname, email, full_name, 
        register_date.strftime("%Y-%m-%d %H:%M:%S"), 
        "active", 
        birth_date.strftime("%Y-%m-%d"), 
        external_id, 
        now.strftime("%Y-%m-%d %H:%M:%S"),
        pages_per_day, 
        books_read_count, 
        DJANGO_HASHED_PWD, 
        1, 0, 0
    ))
    
    user_id = cursor.lastrowid

    # Przypisanie gatunków (korzysta z wag i globalnej listy GENRES)
    selected_genres = random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1, 3))
    
    # Pobiera mapę gatunków, aby uniknąć wielokrotnych SELECTów
    cursor.execute("SELECT name, id FROM genres")
    genre_map = {name: gid for name, gid in cursor.fetchall()}

    for g_name in set(selected_genres):
        g_id = genre_map.get(g_name)
        if g_id:
            cursor.execute("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", 
                           (user_id, g_id))

    conn.commit()
    return user_id

# =================== GENEROWANIE WYZWAŃ ===================
def generate_challenges(conn, users, count_per_user=3):
    cursor = conn.cursor()
    challenges_list = []

    for user in users:
        for _ in range(count_per_user):
            title = f"Challenge {fake.word().capitalize()} {random.randint(1,100)}"
            target_books = random.randint(5, 20)
            progress_books = random.randint(0, target_books)
            start_date = fake.date_time_between(start_date='-6M', end_date='now')
            end_date = start_date + timedelta(days=random.randint(30, 90))

            # określa status
            if progress_books >= target_books:
                status = 'finished'
            elif end_date < datetime.now():
                status = 'failed'
            else:
                status = 'active'

            cursor.execute("""
                INSERT INTO challenges (
                    user_id, title, target_books, progress_books,
                    start_date, end_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user["id"],
                title,
                target_books,
                progress_books,
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                end_date.strftime("%Y-%m-%d %H:%M:%S"),
                status
            ))

            challenges_list.append({
                "user_id": user["id"],
                "title": title,
                "status": status
            })

    conn.commit()
    return challenges_list


# =================== GENEROWANIE KSIĄŻEK ===================
def generate_books(conn, users):
    """Generowanie biblioteki z użyciem executemany dla optymalizacji wydajności."""
    cursor = conn.cursor()
    all_books_data = [] # Lista krotek do executemany
    book_metadata = []  # Pomocnicza lista do zwrócenia wyników
    
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]
    now = datetime.now()

    cursor.execute("SELECT name, id FROM genres")
    genre_map = {name: gid for name, gid in cursor.fetchall()}

    for user in users:
        # Konwersja daty urodzenia, jeśli przyszła jako string (zabezpieczenie spójności)
        bd = user['birth_date']
        if isinstance(bd, str):
            bd = datetime.strptime(bd[:10], "%Y-%m-%d")
        
        # Logika przypisania kategorii wiekowej do preferencji gatunkowych
        age = (now.year - bd.year)
        cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        # Konwersja daty rejestracji (obsługa potencjalnych milisekund z bazy)
        reg_date = user.get('date_joined')
        if isinstance(reg_date, str):
            reg_date = datetime.strptime(reg_date.split('.')[0], "%Y-%m-%d %H:%M:%S")
        
        # Wyliczanie stażu i ratio importu (starsze konta mają więcej książek "historycznych")
        days_on_platform = (now - reg_date).days
        import_ratio = max(0.2, 1.0 - (days_on_platform / 900))

        # Pobieranie liczby książek z profilu użytkownika
        total_finished = user['books_read']
        currently_reading = random.randint(1, 2) if user['status'] == 'active' else 0
        
        for i in range(total_finished + currently_reading):
            is_finished = i < total_finished
            status = 'finished' if is_finished else 'reading'
            
            # Losowanie gatunku: 90% szans na dopasowanie do wieku, 10% na pełen los
            genre_name = random.choice(pref_list) if random.random() < 0.90 else random.choice(GENRES)
            genre_id = genre_map.get(genre_name, 1)

            total_pages = random.randint(150, 600)
            
            # Określenie, czy książka została dodana przez generator (wymaga sesji), czy to stary import
            if status == 'reading':
                is_old_import = False
            else:
                is_old_import = random.random() < import_ratio
            
            if is_old_import:
                current_page = total_pages
                added_by_gen = 0 # Nie generuje sesji dla starych książek
            else:
                current_page = total_pages if is_finished else random.randint(1, total_pages - 1)
                added_by_gen = 1 # Te książki przejdą przez generator aktywności

            # Przygotowanie danych do bazy
            book_title = f"The {random.choice(title_words)} {random.choice(title_words)}"
            author = f"{fake.first_name()} {fake.last_name()}"
            
            all_books_data.append((
                user["id"], book_title, author, genre_id, 
                total_pages, current_page, status, added_by_gen
            ))

            # Zachowanie metadanych dla kolejnych kroków (generate_activity)
            book_metadata.append({
                "user_id": user["id"], 
                "status": status, 
                "total_pages": total_pages,
                "date_joined": reg_date,
                "added_by_generator": added_by_gen
            })

    # BATCH INSERT - optymalizacja zapisu dużej liczby książek
    cursor.executemany("""
        INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, all_books_data)

    # Pobranie ID nowo wstawionych rekordów dla zachowania relacji w meta
    last_id = cursor.lastrowid
    first_id = last_id - len(all_books_data) + 1
    
    for i, meta in enumerate(book_metadata):
        meta["id"] = first_id + i

    conn.commit()
    print(f"SUCCESS: Inserted {len(all_books_data)} books using executemany.")
    return book_metadata


# =================== GENEROWANIE AKTYWNOŚCI ===================
def generate_activity(conn, users, books):
    """
    Symuluje sesje czytania. Dla każdej książki cofa się w czasie od daty 
    zakończenia i generuje sesje (np. 20 stron we wtorek, 40 w sobotę).
    Uwzględnia archetypy, weekendy oraz sezonowość.
    """
    cursor = conn.cursor()
    user_map = {u['id']: u for u in users}
    
    # Filtruje książki, które mają sesje zarejestrowane w aplikacji (nie stary import)
    active_books = [b for b in books if b['added_by_generator'] == 1]
    
    activity_data = []
    book_updates = []

    for b in active_books:
        user = user_map.get(b['user_id'])
        if not user: continue
        
        # Pobieranie nazwy archetypu bezpośrednio z metadanych użytkownika
        arch_name = user.get('r_tier', 'regular')
        arch_data = ARCHETYPE_SETTINGS[arch_name]
        dp_min, dp_max = arch_data["pages_range"]
        
        reg_dt = b.get('date_joined')
        is_finished = b['status'] == 'finished'
        is_inactive = user['status'] == 'inactive'
        
        # Wyznaczanie daty zakończenia (lub punktu odniesienia dla 'reading')
        if is_finished:
            # Książka skończona między rejestracją a dziś (lub porzuceniem konta)
            end_limit = user['last_activity'] if is_inactive else datetime.now()
            
            # Zabezpieczenie przed ujemnym timedelta
            if end_limit <= reg_dt:
                end_limit = reg_dt + timedelta(hours=2)

            finish_dt = fake.date_time_between(
                start_date=reg_dt + timedelta(minutes=60), 
                end_date=end_limit
            )
        else:
            # Książka w trakcie - ostatnia sesja musi być spójna z ostatnią aktywnością
            finish_dt = user['last_activity']

        remaining = b['total_pages'] if is_finished else random.randint(1, b['total_pages'] - 1)
        current_date = finish_dt

        # Generowanie sesji "wstecz" od daty zakończenia
        while remaining > 0:
            # Nie generuje sesji sprzed rejestracji
            if current_date <= reg_dt:
                break

            month = current_date.month
            is_weekend = current_date.weekday() >= 5
            
            # --- LOGIKA ZGODNA Z PARAMETRAMI SYMULACJI ---
            seasonal_factor = SEASONAL_IMPACT.get(month, 1.0)
            
            # Weekend_boost_range z SIM_SETTINGS
            w_min, w_max = SIM_SETTINGS["weekend_boost_range"]
            weekend_multiplier = random.uniform(w_min, w_max) if is_weekend else 1.0
            
            # Bazowa liczba stron z archetypu
            base_pages = random.randint(dp_min, dp_max)
            pages_read = int(base_pages * seasonal_factor * weekend_multiplier)
            
            # Caps & safety (min 1 strona, nie więcej niż zostało)
            pages_read = max(1, min(pages_read, remaining))
            
            # Czas trwania sesji oparty na page_pace_range i min_session_time
            pace_min, pace_max = SIM_SETTINGS["page_pace_range"]
            session_min = int(pages_read * random.uniform(pace_min, pace_max))
            session_min = max(SIM_SETTINGS["min_session_time"], session_min)

            activity_data.append((
                user['id'], b['id'], 
                current_date.strftime("%Y-%m-%d %H:%M:%S"), 
                pages_read, session_min
            ))

            remaining -= pages_read
            
            # Przerwa między sesjami zależna od archetypu (z SIM_SETTINGS)
            if arch_name == 'power':
                gap = random.choice(SIM_SETTINGS["gap_power_user"])
            else:
                gap = random.randint(*SIM_SETTINGS["gap_standard"])
                
            current_date -= timedelta(days=gap)

        # Zbiera daty zakończenia do późniejszego UPDATE
        if is_finished:
            book_updates.append((finish_dt.strftime("%Y-%m-%d %H:%M:%S"), b['id']))

    # BATCH INSERT dla wydajności (zamyka sesje w jednym ruchu)
    cursor.executemany("""
        INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
        VALUES (?, ?, ?, ?, ?)
    """, activity_data)
    
    # Synchronizacja dat zakończenia w tabeli books
    cursor.executemany("UPDATE books SET finish_date = ? WHERE id = ?", book_updates)
    
    conn.commit()
    print(f"SUCCESS: Generated {len(activity_data)} sessions for {len(active_books)} books.")


# =============== AKTUALIZACJA STATYSTYK GATUNKÓW ===================
def update_genre_stats(conn):
    """
    Realizuje obliczenia statystyk dla każdego gatunku.
    Naprawia niespójność między liczbą książek a procentowym udziałem.
    """
    cursor = conn.cursor()
    
    # Liczy całkowitą liczbę ukończonych książek w systemie (suma % wyniesie 100%)
    cursor.execute("SELECT genre_id, COUNT(DISTINCT user_id), COUNT(*) FROM books WHERE status = 'finished' GROUP BY genre_id")
    total_finished_books = cursor.fetchone()[0] or 1

    # Pobranie dostępnych gatunków
    cursor.execute("SELECT id, name FROM genres")
    genres = cursor.fetchall()

    genre_stats = []

    for genre_id, genre_name in genres:
        # Liczba unikalnych czytelników
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM books WHERE genre_id = ?", (genre_id,))
        readers = cursor.fetchone()[0] or 0

        # Średnia ocena
        random.seed(genre_name) 
        avg_rating = round(random.uniform(3.7, 4.9), 2)

        # Liczba przeczytanych książek w danym gatunku
        cursor.execute("""
            SELECT COUNT(*) FROM books 
            WHERE genre_id = ? AND status = 'finished'
        """, (genre_id,))
        books_finished_count = cursor.fetchone()[0] or 0

        # UDZIAŁ: Liczy proporcjonalnie do liczby książek, 
        pct_share = round((books_finished_count / total_finished_books * 100), 2)

        genre_stats.append({
            'id': genre_id,
            'readers': readers,
            'avg_rating': avg_rating,
            'books_read': books_finished_count,
            'share': pct_share
        })

    # Sortuje malejąco po liczbie przeczytanych książek
    genre_stats.sort(key=lambda x: x['books_read'], reverse=True)

    # Aktualizacja bazy danych
    for stat in genre_stats:
        cursor.execute("""
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """, (stat['readers'], stat['avg_rating'], stat['books_read'], stat['share'], stat['id']))

    conn.commit()
    random.seed(datetime.now().timestamp())


#================== AKTUALIZACJA POSTĘPU WYZWAŃ =================    
def update_challenges_progress(conn):
    """
    Synchronizuje postępy w wyzwaniach na podstawie realnie ukończonych książek.
    Aktualizuje kolumnę progress_books oraz status wyzwania.
    """
    cursor = conn.cursor()

    # Przeliczenie postępu: zlicza książki o statusie 'finished' dla każdego użytkownika i porównuje je z czasem trwania wyzwania
    cursor.execute("""
        UPDATE challenges
        SET progress_books = (
            SELECT COUNT(*) 
            FROM books 
            WHERE books.user_id = challenges.user_id 
              AND books.status = 'finished'
              AND books.finish_date BETWEEN challenges.start_date AND challenges.end_date
        )
        WHERE status = 'active'
    """)

    # Automatyczne kończenie wyzwań, które osiągnęły cel
    cursor.execute("""
        UPDATE challenges 
        SET status = 'finished' 
        WHERE status = 'active' AND progress_books >= target_books
    """)

    # Oznaczanie jako 'failed' wyzwań, których termin już minął
    cursor.execute("""
        UPDATE challenges 
        SET status = 'failed' 
        WHERE status = 'active' AND end_date < datetime('now')
    """)

    conn.commit()


#=========== SYMULACJA NOWYCH AKTYWNOŚCI ============
def simulate_incremental_activity(conn, users_meta, books_meta, count=5):
    """Na podstawie książek użytkownika, dodaje aktywność do rozpoczętych lub rozpoczęcie nowej książki), 
    Uwzględnia sezonowość oraz preferencje wiekowe przy wyborze nowej książki 
    """
    cursor = conn.cursor()
    now = datetime.now()
    month = now.month
    
    # Pobiera mapę gatunków
    cursor.execute("SELECT name, id FROM genres")
    genre_map = {name: gid for name, gid in cursor.fetchall()}

    active_users = [u for u in users_meta if u['status'] == 'active']
    
    for _ in range(count):
        user = random.choice(active_users)

        # --- DODATKOWE SPRAWDZENIE (Status w bazie) ---
        cursor.execute("SELECT status FROM users WHERE id = ?", (user['id'],))
        db_res = cursor.fetchone()
        if not db_res or db_res[0] != 'active':
            continue
        
        # --- WYBÓR LUB GENEROWANIE KSIĄŻKI ---
        cursor.execute("SELECT id, current_page, total_pages FROM books WHERE user_id = ? AND status = 'reading'", (user['id'],))
        current_book = cursor.fetchone()
        
        if not current_book:
            # Brak książki 'w trakcie', nowa książka na podstawie logiki preferencji gatunkowej
            age = (now.year - user['birth_date'].year)
            cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
            pref_list = AGE_BASED_GENRES.get(cat, GENRES)
            
            genre_name = random.choice(pref_list) if random.random() < 0.90 else random.choice(GENRES)
            genre_id = genre_map.get(genre_name, 1)
            
            title = f"The {random.choice(['Secret', 'Lost', 'Forgotten'])} {fake.word().capitalize()}"
            total_p = random.randint(150, 600)
            
            cursor.execute("""
                INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
                VALUES (?, ?, ?, ?, ?, 0, 'reading', 1)
            """, (user['id'], title, fake.name(), genre_id, total_p))
            
            book_id = cursor.lastrowid
            curr_p, total_p = 0, total_p
        else:
            book_id, curr_p, total_p = current_book

        # --- WPŁYW SEZONU ---
        seasonal_factor = SEASONAL_IMPACT.get(month, 1.0)
        
        # --- OBLICZENIA SESJI ---
        is_weekend = now.weekday() >= 5
        # Wywołuje bazową funkcję i nakłada sezonowość na wynik
        r_tier = user.r_tier if hasattr(user, 'r_tier') else user.get('r_tier', 'regular')
        pages_read, duration = calculate_session_details(r_tier, is_weekend, total_p - curr_p)
        
        # Modyfikacja o sezon (więcej w zimę, mniej w lato)
        pages_read = max(1, min(int(pages_read * seasonal_factor), total_p - curr_p))
        # Czas trwania wzrasta, skoro więcej stron
        duration = int(duration * seasonal_factor) 

        # --- AKTUALIZACJA BAZY ---
        new_page = curr_p + pages_read
        is_done = new_page >= total_p
        status = 'finished' if is_done else 'reading'
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        # Rejestracja sesji
        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user['id'], book_id, timestamp, pages_read, duration))

        # Update książki
        cursor.execute("""
            UPDATE books SET current_page = ?, status = ?, finish_date = ? WHERE id = ?
        """, (new_page, status, timestamp if is_done else None, book_id))
    
    conn.commit()


# ===================== MAIN (DIAGNOSTYCZNY) =====================
if __name__ == "__main__":
    
    try:
        conn = get_connection()
        print("[OK] Połączenie z bazą danych nawiązane poprawnie.")
        
        # Sprawdzenie czy tabele istnieją
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"[INFO] Znalezione tabele: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"\n[!] BŁĄD POŁĄCZENIA: {e}")
        
    finally:
        if 'conn' in locals():
            conn.close()
            print("[OK] Połączenie zamknięte.")