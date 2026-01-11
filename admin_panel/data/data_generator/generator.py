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


def weighted_age(min_age=12, max_age=75):
    """
    Generuje użytkowników z wszystkich grup wiekowych:
    - 70% - główni użytkownicy (18-45 lat)
    - 15% - seniorzy (60-75 lat)
    - 15% - młodzież (12-17 lat)
    """
    rand = random.random()
    
    if rand < 0.70:
        # Rozkład normalny wokół 30-tki dla głównej grupy
        return int(np.random.normal(30, 7)) % (45 - 18) + 18
    elif rand < 0.85:
        # Seniorzy
        return random.randint(60, max_age)
    else:
        # Młodzież
        return random.randint(min_age, 17)

# =============== USER GENERATOR ===================
def generate_users(conn, count=50):
    """Generuje użytkowników z zachowaniem chronologii i realistycznych statystyk stażu."""
    cursor = conn.cursor()
    users_to_insert = []
    now = datetime.now()
    
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

        status = "active" if random.random() > 0.07 else "inactive"
        
        # Ustalanie daty rejestracji i aktywności
        if status == "inactive":
            register_date = fake.date_time_between(start_date='-2y', end_date='-6M')
            last_activity = fake.date_time_between(start_date=register_date, end_date='-6M')
        else:
            register_date = fake.date_time_between(start_date='-2y', end_date='now')
            last_activity = fake.date_time_between(start_date=register_date, end_date='now')

        account_days = max(1, (now - register_date).days)

        # Skalowanie liczby książek względem stażu konta
        if account_days < 7:
            books_read = random.randint(0, 1)
        else:
            max_possible = max(1, account_days // 15)
            books_read = random.randint(0, min(max_possible, 50))

        # Potencjał stron na dzień dla aktywnych kont
        potential_ppd = round(random.uniform(15.0, 45.0), 1) if status == "active" else 0.0

        users_to_insert.append({
            "name": nickname,
            "register_date": register_date,
            "status": status,
            "age": weighted_age(),
            "external_id": ext_id,
            "last_activity": last_activity,
            "pages_per_day": potential_ppd,
            "books_read": books_read,
            "favorite_genres": random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1,3))
        })

    # Sortowanie chronologiczne przed wstawieniem do bazy dla poprawnego ID
    users_to_insert.sort(key=lambda u: u['register_date'])
    
    inserted_users = []
    for u in users_to_insert:
        cursor.execute("""
            INSERT INTO users (name, register_date, status, age,
                               external_id, last_activity, pages_per_day, books_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (u['name'], u['register_date'].strftime("%Y-%m-%d %H:%M:%S"), u['status'],
              u['age'], u['external_id'], u['last_activity'].strftime("%Y-%m-%d %H:%M:%S"),
              u['pages_per_day'], u['books_read']))
        
        user_id = cursor.lastrowid
        u['id'] = user_id
        inserted_users.append(u)

        for genre in set(u['favorite_genres']):
            cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
            g_id = cursor.fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", (user_id, g_id))

    conn.commit()
    return inserted_users


def generate_realtime_user(conn):
    # Inicjalizacja kursora lokalnego dla funkcji
    cursor = conn.cursor()
    now = datetime.now()

    # Zapewnienie unikalności nazwy użytkownika
    while True:
        nickname = fake.user_name()
        cursor.execute("SELECT 1 FROM users WHERE name = ?", (nickname,))
        if not cursor.fetchone(): 
            break

    # Zapewnienie unikalności identyfikatora zewnętrznego
    while True:
        external_id = random.randint(100000, 999999)
        cursor.execute("SELECT 1 FROM users WHERE external_id = ?", (external_id,))
        if not cursor.fetchone(): 
            break

    # Losowanie parametrów profilu
    age = weighted_age()
    register_date = now - timedelta(hours=random.randint(1, 23))
    
    # Wyliczanie statystyk stron na dzień (zależne od liczby przeczytanych książek)
    books_read_count = random.choices([0, 1], weights=[0.7, 0.3])[0]
    pages_per_day = round(random.uniform(15.0, 35.0), 1) if books_read_count > 0 else 0.0

    # Wstawianie rekordu użytkownika do bazy danych
    cursor.execute("""
        INSERT INTO users (
            name, register_date, status, age,
            external_id, last_activity, pages_per_day, books_read
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nickname, register_date.strftime("%Y-%m-%d %H:%M:%S"),
        "active", age, external_id,
        now.strftime("%Y-%m-%d %H:%M:%S"),
        pages_per_day, books_read_count
    ))
    
    user_id = cursor.lastrowid

    # Generowanie powiązanych rekordów książek i aktywności dla statystyk
    if books_read_count > 0:
        total_p = random.randint(150, 400)
        genre = random.choice(GENRES)
        
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
        cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
        genre_id = cursor.fetchone()[0]

        # Wstawianie ukończonej książki
        cursor.execute("""
            INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, finish_date, added_by_generator)
            VALUES (?, ?, ?, ?, ?, ?, 'finished', ?, 1)
        """, (user_id, f"The {fake.word().capitalize()}", f"{fake.first_name()} {fake.last_name()}", 
              genre_id, total_p, total_p, now.strftime("%Y-%m-%d %H:%M:%S")))
        
        book_id = cursor.lastrowid

        # Dodawanie wpisu do tabeli aktywności dla poprawnego wyliczania Pages/day
        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read)
            VALUES (?, ?, ?, ?)
        """, (user_id, book_id, now.strftime("%Y-%m-%d %H:%M:%S"), random.randint(20, 50)))

    # Przypisywanie ulubionych gatunków
    for g_name in list(set(random.choices(GENRES, weights=GENRE_WEIGHTS, k=random.randint(1, 2)))):
        cursor.execute("SELECT id FROM genres WHERE name = ?", (g_name,))
        res = cursor.fetchone()
        if res:
            cursor.execute("INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)", (user_id, res[0]))

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
    cursor = conn.cursor()
    books = []
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]

    for user in users:
        age = user.get("age", 25) 
        
        if age < 18:
            cat = "junior"
        elif age <= 25:
            cat = "young_adult"
        elif age <= 60:
            cat = "adult"
        else:
            cat = "senior"

        # Pobranie listy preferowanych gatunków dla danej kategorii
        pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        for _ in range(user["books_read"] + random.randint(1, 3)):
            # 85% szans na gatunek z grupy wiekowej, 15% na całkowicie losowy (szum statystyczny)
            if random.random() < 0.85:
                genre_name = random.choice(pref_list)
            else:
                genre_name = random.choice(GENRES)
            
            # Pobieranie/tworzenie genre_id
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre_name,))
            row = cursor.fetchone()
            if row:
                genre_id = row[0]
            else:
                cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre_name,))
                genre_id = cursor.lastrowid

            total_pages = random.randint(120, 800)
            is_finished = random.random() > 0.3
            status = 'finished' if is_finished else 'reading'
            current_page = total_pages if is_finished else random.randint(1, total_pages-1)

            cursor.execute("""
                INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (user["id"], f"The {random.choice(title_words)} {random.choice(title_words)}", 
                  f"{fake.first_name()} {fake.last_name()}", genre_id, total_pages, current_page, status))
            
            books.append({"id": cursor.lastrowid, "user_id": user["id"], "status": status})

    conn.commit()
    return books

# =================== ACTIVITY GENERATOR ===================
def generate_activity(conn, users, books):
    """
    Generuje historię aktywności z naturalnym rozkładem (bonusy weekendowe i piątkowe).
    """
    cursor = conn.cursor()
    finished_books = [b for b in books if b["status"] == "finished"]

    for book in finished_books:
        # Losowanie daty zakończenia
        finish_date = fake.date_time_between(start_date='-2y', end_date='now')
        wd = finish_date.weekday() # 0=Pon, 4=Pią, 5=Sob, 6=Nie
        
        # Losowanie bazowej liczbę stron (np. 15-35)
        base_pages = random.randint(15, 35)
        
        # Mnożnik zależny od dnia tygodnia
        if wd >= 5: # Weekend
            # Bonus 20-50% względem bazy
            multiplier = random.uniform(1.1, 1.4)
        elif wd == 4: # Piątek
            # Bonus 10-25%
            multiplier = random.uniform(1.1, 1.25)
        else: # Dni robocze
            # Czasem (15% szans) trafia się "zaczytany wtorek"
            if random.random() < 0.15:
                multiplier = random.uniform(1.1, 1.4)
            else:
                multiplier = random.uniform(0.7, 1.0)

        pages = min(int(base_pages * multiplier), 50)
        date_str = finish_date.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (book["user_id"], book["id"], date_str, pages, random.randint(20, 60)))

        cursor.execute("UPDATE books SET finish_date = ? WHERE id = ?", (date_str, book["id"]))

    conn.commit()
    print(f"Fixed activity: Generated {len(finished_books)} records with natural week flow.")


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
        # Seed oparty na nazwie zapewnia powtarzalność wyniku dla konkretnego gatunku
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


#=========INCREMENTAL ACTIVITY SIMULATOR=======
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
            # W weekendy użytkownicy czytają więcej (np. 15-40 stron)
            pages_read = random.randint(15, min(40, pages_left))
        else:
            # W dni robocze czytają mniej (np. 1-15 stron)
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

        print("--- Starting database cleanup ---")
        # DROP/CREATE lub sprawdzanie istnienia, aby uniknąć błędów
        tables = ['user_favorite_genres', 'activity', 'challenges', 'books', 'users', 'genres']
        
        for table in tables:
            # Użycie "DELETE FROM" zadziała tylko jeśli tabela istnieje. 
            # Obsługa błędów dla każdej tabeli
            try:
                cursor.execute(f"DELETE FROM {table}")
            except Exception:
                print(f"Skipping cleanup for {table} (table might not exist yet)")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM sqlite_sequence")
        conn.commit()
        cursor.execute("VACUUM") # Optymalizacja rozmiaru pliku
        
        print(f"--- Generating {USER_COUNT} users with realistic age distribution ---")
        users = generate_users(conn, count=USER_COUNT)
        
        print("--- Building library and activity history ---")
        generate_challenges(conn, users)
        books = generate_books(conn, users)
        generate_activity(conn, users, books)
        
        print("--- Recalculating genre analytics ---")
        update_genre_stats(conn)
        
        print("--- GENERATOR FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"CRITICAL ERROR IN GENERATOR: {e}")
        conn.rollback()
    finally:
        conn.close()