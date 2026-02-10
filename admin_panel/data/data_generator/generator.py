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

fake = Faker("pl_PL") # generuje polskich użytkowników

# ============== SEED ==============
# Zapewnia powtarzalność wyników
SEED = 52772
random.seed(SEED)
fake.seed_instance(SEED)

# ============ CONFIG =============
GENRES = [
    "Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical fiction",
    "Crime", "Biography", "Young Adult", "Drama", "Fiction", "Childrens literature"
]

USER_COUNT = 50
BOOK_COUNT = 80
ACTIVITY_COUNT = 200
INACTIVE_PROBABILITY = 0.07  # 7% użytkowników nieaktywnych

# waga gatunków dla ulubionych
GENRE_WEIGHTS = [15, 15, 12, 12, 8, 8, 5, 5, 5, 10, 5]


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
def generate_users(conn, count=50):
    """Generowanie bazy użytkowników z podziałem na grupy aktywności."""
    
    cursor = conn.cursor()
    users_to_insert = []
    now = datetime.now()
    
    # Obliczenie liczby osób nieaktywnych (7%)
    num_inactive = int(count * INACTIVE_PROBABILITY)
    statuses = ["inactive"] * num_inactive + ["active"] * (count - num_inactive)
    random.shuffle(statuses)

    existing_nicknames = set()
    existing_ext_ids = set()

    for i in range(count):
        while True:
            nickname = fake.user_name()
            if nickname not in existing_nicknames:
                existing_nicknames.add(nickname)
                break
        
        while True:
            ext_id = random.randint(100000, 999999)
            if ext_id not in existing_ext_ids:
                existing_ext_ids.add(ext_id)
                break

        status = statuses[i]
        register_date = fake.date_time_between(start_date='-2y', end_date='now')
        
        # Rozdzielenie logiki parametrów
        if status == "inactive":
            # Dane dla konta nieaktywnego
            last_activity = fake.date_time_between(start_date=register_date, end_date='-6M')
            pages_per_day = 0.0  # zero na pages/day
            books_read = random.randint(0, 3) # Minimalny historyczny dorobek
        else:
            # Dane dla konta aktywnego
            last_activity = fake.date_time_between(start_date='-7d', end_date='now')
            pages_per_day = round(random.uniform(10.0, 45.0), 1)
            
            # Wyliczanie realnego dorobku na podstawie stażu i tieru
            days_diff = (now - register_date).days
            account_years = max(0.1, days_diff / 365.25)
            
            # Podział na 4 segmenty intensywności czytania
            r_tier = random.random()
            
            if r_tier < 0.25:    
                # Casual (Czyta sporadycznie, mniej niż 1/miesiąc)
                reader_type = "casual"
                annual_limit = random.randint(1, 11)
                
            elif r_tier < 0.50:  
                # Regular (Czyta ok. 1-2 książki miesięcznie)
                reader_type = "regular"
                annual_limit = random.randint(12, 24)
                
            elif r_tier < 0.75:  
                # Avid (Zapalony czytelnik, prawie 1 tygodniowo)
                reader_type = "avid"
                annual_limit = random.randint(25, 51)
                
            else:                
                # Power (Mol książkowy, ponad 52 książki rocznie)
                reader_type = "power"
                annual_limit = random.randint(52, 60)

            # Wyliczenie książek na podstawie stażu konta i wylosowanego typu czytelnika
            books_read = int(account_years * annual_limit)

        users_to_insert.append({
            "name": nickname,
            "register_date": register_date,
            "status": status,
            "birth_date": generate_birth_date(),
            "external_id": ext_id,
            "last_activity": last_activity,
            "pages_per_day": pages_per_day,
            "books_read": books_read,
            "favorite_genres": random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1,3))
        })

    # Sortowanie i zapis do bazy
    users_to_insert.sort(key=lambda u: u['register_date'])
    inserted_users = []

    for u in users_to_insert:
        cursor.execute("""
            INSERT INTO users (name, register_date, status, birth_date,
                               external_id, last_activity, pages_per_day, books_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            u['name'], 
            u['register_date'].strftime("%Y-%m-%d %H:%M:%S"), 
            u['status'],
            u['birth_date'].strftime("%Y-%m-%d"), 
            u['external_id'], 
            u['last_activity'].strftime("%Y-%m-%d %H:%M:%S"),
            u['pages_per_day'], 
            u['books_read']
        ))
        u['id'] = cursor.lastrowid
        inserted_users.append(u)
        
        for genre in set(u['favorite_genres']):
            cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
            g_id = cursor.fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", 
                           (u['id'], g_id))

    conn.commit()
    return inserted_users


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
    books_read_count = random.choices([0, 1, 2], weights=[0.5, 0.4, 0.1])[0]
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

    # Przypisanie gatunków - Losowanie 1-3 gatunków zgodnie z wagami zdefiniowanymi w CONFIG
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
    """Generowanie biblioteki z zachowaniem korelacji wiekowej dla gatunków."""
    cursor = conn.cursor()
    all_books = []
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]

    for user in users:
        bd = user['birth_date']
        if isinstance(bd, str):
            bd = datetime.strptime(bd, "%Y-%m-%d")
        
        # Wyznaczenie kategorii wiekowej dla dopasowania gatunku
        age = (datetime.now().year - bd.year)
        cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        # Generowanie książek zgodnie z dorobkiem zapisanym w profilu
        total_finished = user['books_read']
        currently_reading = random.randint(1, 2) if user['status'] == 'active' else 0
        
        for i in range(total_finished + currently_reading):
            is_finished = i < total_finished
            status = 'finished' if is_finished else 'reading'
            
            # Wymuszenie korelacji gatunkowej (90% szans na gatunek zgodny z wiekiem)
            genre_name = random.choice(pref_list) if random.random() < 0.90 else random.choice(GENRES)
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre_name,))
            res = cursor.fetchone()
            genre_id = res[0] if res else 1 # Fallback do ID 1 jeśli brak gatunku

            total_pages = random.randint(150, 600)
            current_page = total_pages if is_finished else random.randint(1, total_pages - 1)

            # Zapis rekordu książki do bazy danych
            cursor.execute("""
                INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (user["id"], f"The {random.choice(title_words)} {random.choice(title_words)}", 
                  f"{fake.first_name()} {fake.last_name()}", genre_id, total_pages, current_page, status))
            
            all_books.append({
                "id": cursor.lastrowid, 
                "user_id": user["id"], 
                "status": status, 
                "reg_date": user["register_date"]
            })

    conn.commit()
    return all_books


# =================== ACTIVITY GENERATOR ===================
def generate_activity(conn, users, books):
    cursor = conn.cursor()
    
    user_map = {u['id']: u for u in users}
    finished_books = [b for b in books if b["status"] == "finished"]

    for book in finished_books:
        user = user_map.get(book["user_id"])
        registration_date = user['register_date']
        
        # Rozdzielenie zakresu dat na podstawie statusu użytkownika
        if user['status'] == 'inactive':
            # Aktywność wyłącznie w przeszłości (dawniej niż 6 miesięcy temu)
            finish_date = fake.date_time_between(
                start_date=registration_date, 
                end_date='-6M'
            )
        else:
            # Aktywność w pełnym zakresie od rejestracji do teraz
            finish_date = fake.date_time_between(
                start_date=registration_date, 
                end_date='now'
            )
        
        # Kalkulacja parametrów sesji i wag dni tygodnia
        wd = finish_date.weekday()
        base_pages = random.randint(15, 30)
        
        if wd >= 5: 
            multiplier = random.uniform(1.2, 1.4)
        elif wd == 4: 
            multiplier = random.uniform(1.1, 1.2)
        else: 
            multiplier = random.uniform(0.7, 1.0)

        # Nałożenie limitu 50 stron i przygotowanie danych do zapisu
        pages = min(int(base_pages * multiplier), 50)
        session_time = random.randint(20, 60)
        date_str = finish_date.strftime("%Y-%m-%d %H:%M:%S")

        # Zapis rekordów do tabeli activity oraz aktualizacja tabeli books
        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user["id"], book["id"], date_str, pages, session_time))

        cursor.execute("UPDATE books SET finish_date = ? WHERE id = ?", (date_str, book["id"]))

    conn.commit()
    print(f"Generated {len(finished_books)} records.")


# =================== GENRE STATS UPDATER ===================
def update_genre_stats(conn):
    """
    Realizuje obliczenia statystyk dla każdego gatunku.
    Wygenerowane dane (oceny, udziały) mają charakter realistyczny.
    """
    cursor = conn.cursor()
    
    # Pobranie całkowitej liczby stron dla obliczeń procentowych
    cursor.execute("SELECT SUM(pages_read) FROM activity")
    total_pages = cursor.fetchone()[0] or 0

    # Pobranie dostępnych gatunków
    cursor.execute("SELECT id, name FROM genres")
    genres = cursor.fetchall()

    for genre_id, genre_name in genres:
        # Wyliczenie liczby unikalnych czytelników
        cursor.execute("""
            SELECT COUNT(DISTINCT a.user_id)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        readers = cursor.fetchone()[0] or 0

        # Wygenerowanie realistycznej średniej oceny (zakres 3.7 - 4.9)
        random.seed(genre_name) 
        avg_rating = round(random.uniform(3.7, 4.9), 2)

        # Wyliczenie liczby zarejestrowanych aktywności dla gatunku
        cursor.execute("""
            SELECT COUNT(*)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        books_read = cursor.fetchone()[0] or 0

        # Wyliczenie udziału procentowego w całkowitym czasie czytania
        cursor.execute("""
            SELECT SUM(a.pages_read)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        pages_genre = cursor.fetchone()[0] or 0
        
        pct_total_time = round((pages_genre / total_pages * 100), 2) if total_pages else 0

        # Aktualizacja rekordu w tabeli genres
        cursor.execute("""
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """, (readers, avg_rating, books_read, pct_total_time, genre_id))

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
        current, total = cursor.fetchone()
        
        # Obliczanie stron do końca
        pages_left = total - current
        if pages_left <= 0:
            continue

        # Logika weekendowa:
        now = datetime.now()
        is_weekend = now.weekday() >= 5  # Sobota = 5, Niedziela = 6
        
        if is_weekend:
            # Określenie dolnej granicy (zabezpieczenie przed błędem randint gdy pages_left < 15)
            lower_bound = min(15, pages_left)
            # Określenie górnej granicy (maksymalnie 40 stron lub tyle, ile zostało do końca)
            upper_bound = min(40, pages_left)
            
            pages_read = random.randint(lower_bound, upper_bound)
        else:
            # W dni robocze dolna granica to 1, co jest bezpieczne przy pages_left >= 1
            pages_read = random.randint(1, min(15, pages_left))
        
        new_page = current + pages_read
        status = 'finished' if new_page >= total else 'reading'
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        # Wstawienie nowej aktywności
        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read)
            VALUES (?, ?, ?, ?)
        """, (user['id'], book['id'], timestamp, pages_read))

        # Aktualizacja statusu i strony w tabeli books
        update_query = "UPDATE books SET current_page = ?, status = ? WHERE id = ?"
        params = [new_page, status, book['id']]
        
        # Jeśli książka została skończona, dodaj datę zakończenia
        if status == 'finished':
            update_query = "UPDATE books SET current_page = ?, status = ?, finish_date = ? WHERE id = ?"
            params = [new_page, status, timestamp, book['id']]

        cursor.execute(update_query, tuple(params))
    
    conn.commit()


# ===================== MAIN =====================
if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Usunięcie danych z zachowaniem integralności
        tables = ['user_favorite_genres', 'activity', 'challenges', 'books', 'users', 'genres']
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        
        # Resetowanie liczników autoinkrementacji dla zachowania stałej struktury ID
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'books', 'activity', 'genres')")
        conn.commit()
        
        # Wywołanie procesów generowania danych
        users = generate_users(conn, count=USER_COUNT)
        books = generate_books(conn, users)
        
        generate_challenges(conn, users)
        generate_activity(conn, users, books)
        update_genre_stats(conn)
        update_challenges_progress(conn)
        
        print("--- PROCES ZAKOŃCZONY POMYŚLNIE ---")
        
    except Exception as e:
        print(f"CRITICAL ERROR IN GENERATOR: {e}")
        conn.rollback()
    finally:
        conn.close()