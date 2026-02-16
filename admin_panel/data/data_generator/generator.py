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

# ============== SEED ==============
# Zapewnia powtarzalność wyników
fake = Faker("pl_PL") # generuje polskich użytkowników
SEED = 52772
random.seed(SEED)
fake.seed_instance(SEED)

# ============ CONFIG & CONSTANTS =============
GENRES = [
    "Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical fiction",
    "Crime", "Biography", "Young Adult", "Drama", "Fiction", "Childrens literature"
]

USER_COUNT = 1000
BOOK_COUNT = 80
ACTIVITY_COUNT = 200
INACTIVE_PROBABILITY = 0.07  # 7% użytkowników nieaktywnych
SIX_MONTHS_INACTIVITY = 180

# waga gatunków dla ulubionych
GENRE_WEIGHTS = [15, 15, 12, 12, 8, 8, 5, 5, 5, 10, 5]

# Definicja archetypów czytelniczych
ARCHETYPES = {
    "casual": {"prob": 0.15, "pages": (5, 15), "annual_limit": (1, 6)},
    "regular": {"prob": 0.35, "pages": (15, 25), "annual_limit": (7, 15)},
    "avid": {"prob": 0.60, "pages": (25, 45), "annual_limit": (16, 35)},
    "power": {"prob": 0.85, "pages": (40, 70), "annual_limit": (36, 60)}
    }


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


# =============== USER GENERATOR ===================
def generate_users(conn, count=1000):
    cursor = conn.cursor()
    now = datetime.now()
    
    # --- ZAPEWNIENIE GATUNKÓW ---
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
        nickname = f"{fake.user_name()}_{i}"
        ext_id = 100000 + i
        status = statuses[i]
        register_date = fake.date_time_between(start_date='-2y', end_date='now')
        days_on_platform = (now - register_date).days
        
        # Wylicza staż w latach
        account_years = max(0.1, days_on_platform / 365.25)
        
        # --- LOGIKA BIBLIOTEKI UŻYTKOWNIKA ---
        if status == "inactive":
            if days_on_platform > SIX_MONTHS_INACTIVITY:
                last_activity = fake.date_time_between(
                    start_date=register_date, 
                    end_date=now - timedelta(days=SIX_MONTHS_INACTIVITY)
                )
                active_years = max(0.1, (last_activity - register_date).days / 365.25)
                
                r_tier = random.uniform(0, 0.5) 
                reader_type, annual_limit = ("casual", random.randint(3, 8)) if r_tier < 0.25 else ("regular", random.randint(9, 15))
                
                pages_per_day = 0.0
                books_read = max(1, int(active_years * annual_limit))
            else:
                status = "active"
                last_activity = now
        
        if status == "active":
            activity_start_limit = max(register_date, now - timedelta(days=7))
            last_activity = fake.date_time_between(start_date=activity_start_limit, end_date='now')
            
            r_tier = random.random()
            
            # Dobieranie parametry archetypu
            if r_tier < 0.25:
                reader_type, annual_limit, dp_min, dp_max = "casual", random.randint(3, 11), 2.0, 12.0
            elif r_tier < 0.50:
                reader_type, annual_limit, dp_min, dp_max = "regular", random.randint(12, 24), 12.0, 20.0
            elif r_tier < 0.75:
                reader_type, annual_limit, dp_min, dp_max = "avid", random.randint(25, 51), 20.0, 35.0
            else:
                reader_type, annual_limit, dp_min, dp_max = "power", random.randint(52, 65), 35.0, 50.0

            # Dynamiczne obliczanie książek na podstawie stażu i limitu archetypu
            books_read = max(1, int(account_years * annual_limit))
            pages_per_day = round(random.uniform(dp_min, dp_max), 1)

        temp_users_data.append({
            "db_tuple": (
                nickname, register_date.strftime("%Y-%m-%d %H:%M:%S"), status, 
                generate_birth_date().strftime("%Y-%m-%d"), ext_id, 
                last_activity.strftime("%Y-%m-%d %H:%M:%S"), pages_per_day, books_read
            ),
            "fav_genres": list(set(random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1,3)))),
            "meta": {
                "id_tier": r_tier, "r_tier": reader_type, "name": nickname, 
                "register_date": register_date, "status": status, "books_read": books_read,
                "birth_date": None, "last_activity": last_activity 
            }
        })

    # Zachowana logika sortowania i insertów
    temp_users_data.sort(key=lambda u: u['meta']['register_date'])

    cursor.executemany("""
        INSERT INTO users (name, register_date, status, birth_date,
                           external_id, last_activity, pages_per_day, books_read)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [u['db_tuple'] for u in temp_users_data])

    # --- POBIERANIE ID DLA RELACJI ---
    cursor.execute("SELECT id, name FROM users ORDER BY id DESC LIMIT ?", (count,))
    db_users = {name: uid for uid, name in cursor.fetchall()}
    
    favorite_genres_tuples = []
    inserted_users_meta = []

    for u in temp_users_data:
        u_name = u['meta']['name']
        user_id = db_users.get(u_name)
        if not user_id: continue
        
        u['meta']['id'] = user_id
        u['meta']['birth_date'] = u['db_tuple'][3]
        inserted_users_meta.append(u['meta'])

        for g_name in u['fav_genres']:
            g_id = genre_map.get(g_name)
            if g_id:
                favorite_genres_tuples.append((user_id, g_id))

    cursor.executemany("""
        INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) 
        VALUES (?, ?)
    """, favorite_genres_tuples)

    conn.commit()
    print(f"SUCCESS: Inserted {len(inserted_users_meta)} users and {len(favorite_genres_tuples)} favorite genre relations.")
    return inserted_users_meta


def generate_realtime_user(conn):
    """
    Symuluje rejestrację nowego użytkownika w czasie rzeczywistym z minimalnym dorobkiem."""
    cursor = conn.cursor()
    now = datetime.now()

    # Logika unikalności danych identyfikacyjnych
    while True:
        nickname = fake.user_name()
        cursor.execute("SELECT 1 FROM users WHERE name = ?", (nickname,))
        if not cursor.fetchone(): break
    while True:
        external_id = random.randint(100000, 999999)
        cursor.execute("SELECT 1 FROM users WHERE external_id = ?", (external_id,))
        if not cursor.fetchone(): break

    birth_date = generate_birth_date()
    register_date = now - timedelta(hours=random.randint(1, 23))
    
    # Parametry startowe profilu
    books_read_count = random.choices([1, 2], weights=[0.5, 0.5])[0]
    pages_per_day = round(random.uniform(15.0, 35.0), 1)

    # Wstawienie rekordu użytkownika
    cursor.execute("""
        INSERT INTO users (name, register_date, status, birth_date, external_id, 
                           last_activity, pages_per_day, books_read)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nickname, register_date.strftime("%Y-%m-%d %H:%M:%S"), "active", 
          birth_date.strftime("%Y-%m-%d"), external_id, now.strftime("%Y-%m-%d %H:%M:%S"),
          pages_per_day, books_read_count))
    
    user_id = cursor.lastrowid

    # Przypisanie gatunków - Losowanie 1-3 gatunków
    selected_genres = random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1, 3))
    
    for genre in set(selected_genres):
        # Zapewnienie istnienia gatunku w słowniku i pobranie jego ID
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
        cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
        g_id = cursor.fetchone()[0]
        
        # Powiązanie użytkownika z gatunkiem w tabeli łączącej
        cursor.execute("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", 
                       (user_id, g_id))

    conn.commit()
    return user_id

# =================== CHALLENGES GENERATOR ===================
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


# Słownik preferencji: Gatunek -> Prawdopodobieństwo wystąpienia w danej grupie
AGE_BASED_GENRES = {
    "junior": ["Childrens literature", "Fantasy", "Young Adult"],
    "young_adult": ["Young Adult", "Romance", "Drama", "Fantasy", "Sci-Fi"],
    "adult": ["Crime", "Thriller", "Fiction", "Biography", "Historical fiction"],
    "senior": ["Historical fiction", "Biography", "Crime", "Drama"]
}


# =================== BOOKS GENERATOR ===================
def generate_books(conn, users):
    """Generowanie biblioteki z użyciem executemany dla optymalizacji wydajności."""
    cursor = conn.cursor()
    all_books_data = [] # Lista krotek do executemany
    book_metadata = []   # Pomocnicza lista do zwrócenia wyników
    
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]
    now = datetime.now()

    cursor.execute("SELECT name, id FROM genres")
    genre_map = {name: gid for name, gid in cursor.fetchall()}

    for user in users:
        bd = user['birth_date']
        if isinstance(bd, str):
            bd = datetime.strptime(bd, "%Y-%m-%d")
        
        age = (now.year - bd.year)
        cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        reg_date = user['register_date']
        if isinstance(reg_date, str):
            reg_date = datetime.strptime(reg_date.split('.')[0], "%Y-%m-%d %H:%M:%S")
        
        days_on_platform = (now - reg_date).days
        import_ratio = max(0.2, 1.0 - (days_on_platform / 900))

        total_finished = user['books_read']
        currently_reading = random.randint(1, 2) if user['status'] == 'active' else 0
        
        for i in range(total_finished + currently_reading):
            is_finished = i < total_finished
            status = 'finished' if is_finished else 'reading'
            
            genre_name = random.choice(pref_list) if random.random() < 0.90 else random.choice(GENRES)
            genre_id = genre_map.get(genre_name, 1)

            total_pages = random.randint(150, 600)
            
            if status == 'reading':
                is_old_import = False
            else:
                is_old_import = random.random() < import_ratio
            
            if is_old_import:
                current_page = total_pages
                added_by_gen = 0
            else:
                current_page = total_pages if is_finished else random.randint(1, total_pages - 1)
                added_by_gen = 1

            # Przygotowanie danych do bazy
            book_title = f"The {random.choice(title_words)} {random.choice(title_words)}"
            author = f"{fake.first_name()} {fake.last_name()}"
            
            all_books_data.append((
                user["id"], book_title, author, genre_id, 
                total_pages, current_page, status, added_by_gen
            ))

            # Zachowanie metadanych
            book_metadata.append({
                "user_id": user["id"], 
                "status": status, 
                "total_pages": total_pages,
                "reg_date": reg_date,
                "added_by_generator": added_by_gen
            })

    # BATCH INSERT
    cursor.executemany("""
        INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, all_books_data)

    # POBRANIE ID
    last_id = cursor.lastrowid
    first_id = last_id - len(all_books_data) + 1
    
    for i, meta in enumerate(book_metadata):
        meta["id"] = first_id + i

    conn.commit()
    print(f"SUCCESS: Inserted {len(all_books_data)} books using executemany.")
    return book_metadata


# =================== ACTIVITY GENERATOR ===================
def generate_activity(conn, users, books):
    """
    Generuje realistyczną historię czytania dla książek oznaczonych do procesowania.
    Uwzględnia archetypy, weekendy oraz sezonowość.
    """
    cursor = conn.cursor()
    user_map = {u['id']: u for u in users}
    
    # Filtruje książki, mają sesje zarejestrowane w aplikacji
    active_books = [b for b in books if b['added_by_generator'] == 1]
    
    activity_data = []
    book_updates = []

    # Mapowanie sezonowości (zima/jesień = więcej czytania, lato = mniej)
    season_map = {
        1: 1.6, 2: 1.5, 3: 1.1, 4: 0.8, 5: 0.7, 6: 0.6,
        7: 0.8, 8: 0.9, 9: 1.1, 10: 1.3, 11: 1.5, 12: 1.7
    }

    for b in active_books:
        user = user_map.get(b['user_id'])
        if not user: continue
        
        # Pobiera parametry archetypu
        arch = ARCHETYPES.get(user.get('r_tier', 'regular'), ARCHETYPES['regular'])
        pages_min, pages_max = arch['pages']
        
        reg_dt = b['reg_date']
        is_finished = b['status'] == 'finished'
        is_inactive = user['status'] == 'inactive'
        
        # Wyznaczanie daty zakończenia (lub ostatniej aktywności dla 'reading')
        if is_finished:
            # Książka skończona w dowolnym momencie od rejestracji do dziś (lub do porzucenia appki)
            end_limit = user['last_activity'] if is_inactive else datetime.now()
            finish_dt = fake.date_time_between(
                start_date=reg_dt + timedelta(minutes=60), 
                end_date=end_limit
            )
        else:
            # Książka w trakcie - ostatnia sesja musi być blisko 'last_activity'
            finish_dt = user['last_activity']

        remaining = b['total_pages'] if is_finished else random.randint(1, b['total_pages'] - 1)
        current_date = finish_dt

        # Generowanie sesji "wstecz" od daty zakończenia
        while remaining > 0:
            # Nie przed rejestracją
            if current_date <= reg_dt:
                break

            month = current_date.month
            is_weekend = current_date.weekday() >= 5
            
            # Składowe tempa czytania
            seasonal_factor = season_map.get(month, 1.0)
            weekend_multiplier = random.uniform(1.3, 1.8) if is_weekend else 1.0
            
            # Bazowa liczba stron z archetypu
            base_pages = random.randint(pages_min, pages_max)
            pages_read = int(base_pages * seasonal_factor * weekend_multiplier)
            
            # Caps & safety
            pages_read = max(1, min(pages_read, remaining))
            session_min = max(5, int(pages_read * random.uniform(0.8, 1.5))) # ok. 1 min na stronę

            activity_data.append((
                user['id'], b['id'], 
                current_date.strftime("%Y-%m-%d %H:%M:%S"), 
                pages_read, session_min
            ))

            remaining -= pages_read
            
            # Przerwa między sesjami: archetypy 'power' czytają codziennie, 'casual' co kilka dni
            if user.get('r_tier') == 'power':
                gap = random.choice([1, 1, 1, 2])
            else:
                gap = random.randint(1, 4)
                
            current_date -= timedelta(days=gap)

        if is_finished:
            book_updates.append((finish_dt.strftime("%Y-%m-%d %H:%M:%S"), b['id']))

    # Bulk insert dla wydajności
    cursor.executemany("""
        INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
        VALUES (?, ?, ?, ?, ?)
    """, activity_data)
    
    cursor.executemany("UPDATE books SET finish_date = ? WHERE id = ?", book_updates)
    
    conn.commit()
    print(f"SUCCESS: Generated {len(activity_data)} sessions for {len(active_books)} active books.")


# =================== GENRE STATS UPDATER ===================
def update_genre_stats(conn):
    """
    Realizuje obliczenia statystyk dla każdego gatunku.
    Naprawia niespójność między liczbą książek a procentowym udziałem.
    """
    cursor = conn.cursor()
    
    # Liczy całkowitą liczbę ukończonych książek w systemie (suma % wyniesie 100%)
    cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'finished'")
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


#========= AKTUALIZACJA WYZWAŃ ==========    
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


#======== INCREMENTAL ACTIVITY SIMULATOR =======
def simulate_incremental_activity(conn, users, books, count=1):
    cursor = conn.cursor()
    for _ in range(count):
        user = random.choice(users)
        user_books = [b for b in books if b['user_id'] == user['id'] and b['status'] == 'reading']
        
        if not user_books:
            continue
            
        book = random.choice(user_books)
        
        cursor.execute("SELECT current_page, total_pages FROM books WHERE id = ?", (book['id'],))
        result = cursor.fetchone()
        if not result: continue
        current, total = result
        
        # Obliczanie stron do końca
        pages_left = total - current
        if pages_left <= 0:
            continue
        
        # Logika weekendowa
        now = datetime.now()
        is_weekend = now.weekday() >= 5 
        
        if is_weekend:
            pages_read = random.randint(min(15, pages_left), min(40, pages_left))
        else:
            pages_read = random.randint(1, min(15, pages_left))
        
        # Oblicznie czasu sesji
        session_min = max(2, int(pages_read * random.uniform(0.9, 1.4)))

        new_page = current + pages_read
        status = 'finished' if new_page >= total else 'reading'
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user['id'], book['id'], timestamp, pages_read, session_min))

        # Aktualizacja statusu i strony
        if status == 'finished':
            cursor.execute("""
                UPDATE books SET current_page = ?, status = ?, finish_date = ? WHERE id = ?
            """, (new_page, status, timestamp, book['id']))
        else:
            cursor.execute("""
                UPDATE books SET current_page = ?, status = ? WHERE id = ?
            """, (new_page, status, book['id']))
    
    conn.commit()


# ===================== MAIN =====================
if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Usunięcie danych
        tables = ['user_favorite_genres', 'activity', 'challenges', 'books', 'users', 'genres']
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        
        # Resetowanie sekwencji ID
        cursor.execute("DELETE FROM sqlite_sequence")
        conn.commit()
        
        # Proces generowania
        users = generate_users(conn, count=USER_COUNT)
        books = generate_books(conn, users)
        
        generate_challenges(conn, users)
        generate_activity(conn, users, books)
        update_genre_stats(conn)
        update_challenges_progress(conn)
        
        print("--- PROCES ZAKOŃCZONY POMYŚLNIE ---")
        
    except Exception as e:
        print(f"CRITICAL ERROR IN GENERATOR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()