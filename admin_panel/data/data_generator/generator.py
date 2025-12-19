import random
from datetime import datetime, timedelta
from faker import Faker
import sys
import math
from pathlib import Path

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
INACTIVE_PROBABILITY = 0.05  # 5% użytkowników nieaktywnych

# waga gatunków dla ulubionych
GENRE_WEIGHTS = [15, 15, 12, 12, 8, 8, 5, 5, 5, 10, 5]


# =============== USER GENERATOR ===================
def generate_users(conn, count=USER_COUNT):
    """
    Tworzy użytkowników z realistycznym books_read i pages_per_day powiązanym z czasem konta.
    """
    cursor = conn.cursor()
    users = []

    cursor.execute("SELECT external_id, name FROM users")
    rows = cursor.fetchall()
    external_ids = {r[0] for r in rows}
    existing_nicknames = {r[1] for r in rows}
    runtime_nicknames = set()

    def generate_external_id():
        while True:
            eid = random.randint(100000, 999999)
            if eid not in external_ids:
                external_ids.add(eid)
                return eid

    now = datetime.now()

    for _ in range(count):
        # generuje unikalny nickname
        while True:
            nickname = fake.user_name()
            if nickname not in existing_nicknames and nickname not in runtime_nicknames:
                existing_nicknames.add(nickname)
                runtime_nicknames.add(nickname)
                break

        age = random.randint(12, 80)
        external_id = generate_external_id()
        status = "inactive" if random.random() < INACTIVE_PROBABILITY else "active"

        # wybieramy czas rejestracji
        if status == "inactive":
            register_date = fake.date_time_between(start_date='-4y', end_date='-6M')
        else:
            register_date = fake.date_time_between(start_date='-4y', end_date='-1d')

        account_days = max(1, (now - register_date).days)

        # books_read – zależne od wieku konta i typu użytkownika
        if status == "inactive":
            books_read = max(1, int(random.uniform(0.1, 0.3) * account_days / 30))
            pages_per_day = None
        else:
            # większość użytkowników średnia, mała grupa aktywnych z dużo książkami
            avg_books_per_month = random.choices(
                population=[0.5, 0.8, 1, 1.2, 1.5], 
                weights=[0.1, 0.2, 0.4, 0.2, 0.1],
                k=1
            )[0]
            books_read = max(1, min(31, int(avg_books_per_month * (account_days / 30) + random.gauss(0, 2))))
            pages_per_day = round(random.uniform(15, 50), 1)

        # losowe ostatnie logowanie
        last_activity = register_date + timedelta(days=random.randint(0, account_days))
        if status == "active":
            last_activity = now

        cursor.execute("""
            INSERT INTO users (
                name, register_date, status, age,
                external_id, last_activity,
                pages_per_day, books_read
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nickname,
            register_date.strftime("%Y-%m-%d %H:%M:%S"),
            status,
            age,
            external_id,
            last_activity.strftime("%Y-%m-%d %H:%M:%S"),
            pages_per_day,
            books_read
        ))

        user_id = cursor.lastrowid

        # ---------------- ulubione gatunki ----------------
        weighted_choices = random.choices(GENRES, weights=GENRE_WEIGHTS, k=5)
        favorite_genres = list(set(weighted_choices))[:random.randint(1, 3)]
        for genre in favorite_genres:
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
            row = cursor.fetchone()
            if row:
                genre_id = row[0]
            else:
                cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre,))
                genre_id = cursor.lastrowid
            cursor.execute("""
                INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id)
                VALUES (?, ?)
            """, (user_id, genre_id))

        users.append({
            "id": user_id,
            "status": status,
            "register_date": register_date,
            "last_activity": last_activity,
            "books_read": books_read,
            "pages_per_day": pages_per_day
        })

    conn.commit()
    return users


def generate_realtime_user(conn):
    """
    Generuje pojedynczego użytkownika w czasie rzeczywistym.
    register_date: maksymalnie wczoraj/dzisiaj
    last_activity: teraz
    """
    cursor = conn.cursor()
    now = datetime.now()

    # generowanie unikalnego nickname i external_id
    while True:
        nickname = fake.user_name()
        cursor.execute("SELECT 1 FROM users WHERE name = ?", (nickname,))
        if not cursor.fetchone():
            break

    while True:
        external_id = random.randint(100000, 999999)
        cursor.execute("SELECT 1 FROM users WHERE external_id = ?", (external_id,))
        if not cursor.fetchone():
            break

    status = "active"
    age = random.randint(12, 80)
    register_date = fake.date_time_between(start_date='-1d', end_date='now')
    last_activity = datetime.now()

    pages_per_day = round(random.uniform(10, 35), 1)
    books_read = random.randint(1, 3)

    cursor.execute("""
        INSERT INTO users (
            name, register_date, status, age,
            external_id, last_activity, pages_per_day, books_read
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nickname, register_date.strftime("%Y-%m-%d %H:%M:%S"),
        status, age, external_id,
        last_activity.strftime("%Y-%m-%d %H:%M:%S"),
        pages_per_day, books_read
    ))
    conn.commit()
    user_id = cursor.lastrowid

    # ---------------- ulubione gatunki ----------------
    weighted_choices = random.choices(GENRES, weights=GENRE_WEIGHTS, k=5)
    favorite_genres = list(set(weighted_choices))[:random.randint(1, 3)]
    for genre in favorite_genres:
        cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
        row = cursor.fetchone()
        if row:
            genre_id = row[0]
        else:
            cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre,))
            genre_id = cursor.lastrowid
        cursor.execute("""
            INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id)
            VALUES (?, ?)
        """, (user_id, genre_id))

    print(f"[REALTIME] Added user {nickname} with id {user_id}")
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

            # określamy status
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


# =================== BOOKS GENERATOR ===================
def generate_books(conn, users, count=BOOK_COUNT):
    """
    Tworzy książki przypisane losowo do użytkowników.
    - Wybór tytułu i autora z generatora Faker.
    - Przypisanie gatunku (z istniejących lub tworzenie nowego).
    - Zapisywanie do tabeli 'books'.
    """
    cursor = conn.cursor()
    books = []
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]

    for _ in range(count):
        user = random.choice(users)
        title = f"The {random.choice(title_words)} {random.choice(title_words)}"
        author = f"{fake.first_name()} {fake.last_name()}"
        total_pages = random.randint(120, 1000)  # do 1000 stron

        genre = random.choice(GENRES)
        cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
        row = cursor.fetchone()
        if row:
            genre_id = row[0]
        else:
            cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre,))
            genre_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO books (user_id, title, authors, genre_id, total_pages, current_page, status, added_by_generator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user["id"], title, author, genre_id, total_pages, 0, "reading", 1))

        book_id = cursor.lastrowid
        books.append({"id": book_id, "user_id": user["id"], "total_pages": total_pages, "genre_id": genre_id})

    conn.commit()
    return books

# =================== ACTIVITY GENERATOR ===================
def generate_activity(conn, users, books, count=ACTIVITY_COUNT):
    """
    Tworzy sesje czytelnicze dla aktywnych użytkowników.
    - Losuje książki i daty czytania w realistycznym zakresie.
    - Generuje pages_read i session_minutes.
    - Aktualizuje 'last_activity' w tabeli users.
    """
    cursor = conn.cursor()
    activity_list = []

    active_users = [u for u in users if u["status"] == "active"]
    if not active_users or not books:
        return activity_list

    for _ in range(count):
        user = random.choice(active_users)
        book = random.choice(books)

        user_register = user["register_date"]
        start_date = fake.date_time_between(
            start_date=max(user_register, datetime.now() - timedelta(days=90)),
            end_date=datetime.now()  # tutaj po prostu teraz, bo end_date jeszcze nie istnieje
        )

        duration_days = random.randint(1, 14)
        end_date = start_date + timedelta(
            days=duration_days,
            hours=random.randint(0,23),
            minutes=random.randint(0,59)
        )

        # upewniamy się, że end_date nie przekracza teraz
        end_date = min(end_date, datetime.now())

        # realistyczne pages_read
        if random.random() < 0.3:
            pages_read = 0
        else:
            max_pages = min(book["total_pages"], 50)  # max 50 na sesję
            pages_read = random.randint(1, max(1, max_pages))

        session_minutes = max(10, pages_read) + random.randint(0,30)

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user["id"], book["id"], end_date.strftime("%Y-%m-%d %H:%M:%S"), pages_read, session_minutes))

        # Pobieramy obecne pages_per_day i aktualizujemy last_activity
        cursor.execute("SELECT pages_per_day FROM users WHERE id = ?", (user["id"],))
        pages_per_day = cursor.fetchone()[0] or round(random.uniform(5,50),1)

        # update books_read i last_activity
        cursor.execute("""
            UPDATE users
            SET last_activity = ?
            WHERE id = ?
        """, (end_date.strftime("%Y-%m-%d %H:%M:%S"), user["id"]))

        activity_list.append({"user_id": user["id"], "book_id": book["id"], "pages_read": pages_read})

    conn.commit()
    return activity_list

# =================== GENRE STATS UPDATER ===================
def update_genre_stats(conn):
    """
    Oblicza statystyki dla każdego gatunku:
    - liczba czytelników (readers)
    - średnia ocena książek (avg_rating)
    - liczba przeczytanych książek (books_read)
    - udział w czasie czytania (reading_time_share)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pages_read) FROM activity")
    total_pages = cursor.fetchone()[0] or 0

    cursor.execute("SELECT id, name FROM genres")
    genres = cursor.fetchall()

    for genre_id, genre_name in genres:
        cursor.execute("""
            SELECT COUNT(DISTINCT a.user_id)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        readers = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT AVG(3 + RANDOM() % 3)
            FROM books
            WHERE genre_id = ?
        """, (genre_id,))
        avg_rating = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        books_read = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT SUM(a.pages_read)
            FROM activity a
            JOIN books b ON a.book_id = b.id
            WHERE b.genre_id = ?
        """, (genre_id,))
        pages_genre = cursor.fetchone()[0] or 0
        pct_total_time = round((pages_genre / total_pages * 100), 2) if total_pages else 0

        cursor.execute("""
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """, (readers, avg_rating, books_read, pct_total_time, genre_id))

    conn.commit()

#=========INCREMENTAL ACTIVITY SIMULATOR=======
def simulate_incremental_activity(conn, users, books, count=10):
    """
    Dodaje nowe aktywności dla aktywnych użytkowników w czasie rzeczywistym.
    - Aktualizuje pages_per_day i books_read jeśli użytkownik faktycznie czytał.
    - Umożliwia "odświeżenie" danych w dashboardzie bez generowania całej historii.
    """
    cursor = conn.cursor()
    activity_list = []

    active_users = [u for u in users if u["status"] == "active"]
    if not active_users or not books:
        return activity_list

    for _ in range(count):
        user = random.choice(active_users)
        user_books = [b for b in books if b["user_id"] == user["id"]]
        if not user_books:
            continue
        book = random.choice(user_books)

        start_date = fake.date_time_between(start_date='-1d', end_date='now')
        duration_days = random.randint(0, 2)
        end_date = start_date + timedelta(days=duration_days,
                                  hours=random.randint(0, 2),
                                  minutes=random.randint(0, 59))
        # ograniczenie do teraz
        if end_date > datetime.now():
            end_date = datetime.now()

        # realistyczne pages_read
        if random.random() < 0.2:
            pages_read = 0
        else:
            max_pages = min(book["total_pages"], 50)
            pages_read = random.randint(1, max(1, max_pages))

        session_minutes = max(5, pages_read) + random.randint(0, 10)

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user["id"], book["id"], end_date.strftime("%Y-%m-%d %H:%M:%S"), pages_read, session_minutes))

        # aktualizacja last_activity
        cursor.execute("""
            UPDATE users
            SET last_activity = ?
            WHERE id = ?
        """, (end_date.strftime("%Y-%m-%d %H:%M:%S"), user["id"]))

        # tylko dla active users aktualizuje pages_per_day i books_read
        if pages_read >= 20:
            cursor.execute("""
                UPDATE users
                SET
                    books_read = books_read + 1,
                    pages_per_day = MIN(
                        50,
                        MAX(
                            5,
                            COALESCE(pages_per_day, 20) + ?
                        )
                    )
                WHERE id = ?
            """, (round(random.uniform(-1.0, 2.0), 1), user["id"]))

        activity_list.append({"user_id": user["id"], "book_id": book["id"], "pages_read": pages_read})

    conn.commit()
    print(f"[INCREMENT] Added {len(activity_list)} activity records")
    return activity_list


# ===================== MAIN =====================
if __name__ == "__main__":
    conn = get_connection()
    users = generate_users(conn)
    challenges = generate_challenges(conn, users)
    books = generate_books(conn, users)
    activity = generate_activity(conn, users, books)
    
    update_genre_stats(conn)

    print(f"Generated {len(challenges)} challenges")
    print(f"Generated {len(users)} users, {len(books)} books, {len(activity)} activity records")
    print("Genre statistics updated successfully.")