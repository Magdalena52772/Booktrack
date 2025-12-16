import random
from datetime import datetime, timedelta
from faker import Faker
import sys
from pathlib import Path

# ================= PATH FIX =================
BASE_DIR = Path(__file__).resolve().parent.parent  # admin_panel/data
sys.path.append(str(BASE_DIR.parent))  # dodaje admin_panel do sys.path

from data.database import get_connection  # teraz działa

fake = Faker("pl_PL")

# ============ CONFIG =============
GENRES = [
    "Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical fiction",
    "Crime", "Biography", "Young Adult", "Drama", "Fiction", "Childrens literature"
]

USER_COUNT = 50
BOOK_COUNT = 80
ACTIVITY_COUNT = 200




# =================== USER GENERATOR ===================
def generate_users(conn, count=USER_COUNT):
    cursor = conn.cursor()
    users = []
    nicknames = set()

    for _ in range(count):
        # generujemy unikalny nickname
        while True:
            nickname = fake.user_name()
            if nickname not in nicknames:
                nicknames.add(nickname)
                break

        register_date = fake.date_time_between(start_date='-4y', end_date='now')
        cursor.execute("""
            INSERT INTO users (name, register_date, status)
            VALUES (?, ?, ?)
        """, (nickname, register_date.strftime("%Y-%m-%d %H:%M:%S"), "active"))

        user_id = cursor.lastrowid

        # ulubione gatunki
        favorite_genres = random.sample(GENRES, k=random.randint(1, 3))
        for genre in favorite_genres:
            cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,))
            row = cursor.fetchone()
            if row:
                genre_id = row[0]
            else:
                cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre,))
                genre_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO user_favorite_genres (user_id, genre_id)
                VALUES (?, ?)
            """, (user_id, genre_id))

        users.append({"id": user_id, "nickname": nickname})

    conn.commit()
    return users


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
    cursor = conn.cursor()
    books = []
    title_words = ["Shadow", "Forest", "Dream", "Fire", "Storm", "Heart", "Secret", "Moon", "Whisper", "Glass"]

    for _ in range(count):
        user = random.choice(users)
        title = f"The {random.choice(title_words)} {random.choice(title_words)}"
        author = f"{fake.first_name()} {fake.last_name()}"
        total_pages = random.randint(120, 700)

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
    cursor = conn.cursor()
    activity_list = []

    for _ in range(count):
        user = random.choice(users)
        book = random.choice(books)

        start_date = fake.date_time_between(start_date='-3M', end_date='now')
        duration_days = random.randint(1, 14)
        end_date = start_date + timedelta(days=duration_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        pages_read = random.randint(1, book["total_pages"])
        session_minutes = random.randint(10, 120)

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user["id"], book["id"], end_date.strftime("%Y-%m-%d %H:%M:%S"), pages_read, session_minutes))

        # aktualizacja statystyk użytkownika
        cursor.execute("""
            UPDATE users
            SET books_read = books_read + 1,
                pages_per_day = ROUND((pages_per_day + (? / ?)) / 2, 1),
                last_activity = ?
            WHERE id = ?
        """, (pages_read, max(duration_days, 1), end_date.strftime("%Y-%m-%d %H:%M:%S"), user["id"]))

        activity_list.append({"user_id": user["id"], "book_id": book["id"], "pages_read": pages_read})

    conn.commit()
    return activity_list

# =================== GENRE STATS UPDATER ===================
def update_genre_stats(conn):
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
