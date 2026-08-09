from pathlib import Path
import sys

# Zapewnienie UTF-8 dla stdout, aby poprawnie wyświetlać polskie znaki i emoji w konsoli
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_FILE = Path(__file__).resolve().parent / "test_booktrack.db"

sys.path.insert(0, str(REPO_ROOT))

from data import database as dbmod
from data.config import database as cfg_db

# Nadpisanie ścieżki do bazy danych w konfiguracji, aby testy były izolowane i nie wpływały na produkcyjną bazę danych
dbmod.DB_PATH = DB_FILE
cfg_db.DB_PATH = DB_FILE

from data.database import initialize_database, get_connection


def run():
    if DB_FILE.exists():
        DB_FILE.unlink()

    initialize_database()
    conn = get_connection()

    # Importowanie funkcji generujących dane i symulujących aktywność
    from data.data_generator.users import generate_users
    from data.data_generator.books import generate_books, _load_book_pool
    from data.data_generator.activity import simulate_incremental_activity

    users = generate_users(conn, count=100)
    books_meta = generate_books(conn, users)

    pool_all, pool_by_genre = _load_book_pool()

    # Symulacja aktywności użytkowników na podstawie wygenerowanych danych (książki, preferencje, itp.)
    logs = simulate_incremental_activity(conn, users, books_meta, count=20)

    # Podsumowanie wyników i walidacja danych w bazie po symulacji
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM books")
    books_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM books WHERE openlibrary_id IS NOT NULL")
    books_with_pool = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM activity")
    activity_total = cur.fetchone()[0]

    # Sprawdzenie meta.last_activity dla szybkiego wglądu w ostatnią aktywność (testuje mechanizm aktualizacji meta podczas symulacji)
    meta_val = None
    try:
        cur.execute("SELECT v FROM meta WHERE k = 'last_activity'")
        r = cur.fetchone()
        meta_val = r[0] if r else None
    except Exception:
        meta_val = None

    # Pobranie kilku przykładowych książek z bazy, aby zweryfikować poprawność danych i integrację z pulą książek
    cur.execute("SELECT id, title, openlibrary_id FROM books ORDER BY id DESC LIMIT 5")
    sample_books = cur.fetchall()

    # Dodatkowa walidacja: sprawdzenie, czy książki z pulą są poprawnie przypisane do użytkowników i czy gatunki są zgodne z preferencjami (jeśli są dostępne)
    from data.utils.helpers.date_helpers import DateHelper
    from data.config import AGE_BASED_GENRES

    cur.execute("""
        SELECT u.id, u.username, u.birth_date, COUNT(b.id) as book_count
        FROM users u
        LEFT JOIN user_books ub ON u.id = ub.user_id
        LEFT JOIN books b ON ub.book_id = b.id
        GROUP BY u.id
        LIMIT 10
    """)
    sample_users = cur.fetchall()

    genre_bias_checks = []
    for uid, username, birth_date_str, book_count in sample_users:
        if book_count == 0:
            continue

        # Pobranie ulubionych gatunków użytkownika
        cur.execute(
            "SELECT g.name FROM user_favorite_genres ufg JOIN genres g ON ufg.genre_id = g.id WHERE ufg.user_id = ?",
            (uid,),
        )
        fav_genres = [row[0] for row in cur.fetchall()]

        # Dopasowanie puli gatunków do wieku użytkownika (segmentacja demograficzna)
        bd = DateHelper.to_datetime(birth_date_str)
        age = DateHelper.calculate_age(bd)
        cat = (
            "junior"
            if age < 18
            else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        )
        age_genres = AGE_BASED_GENRES.get(cat, [])

        # Pobranie gatunków książek przeczytanych przez użytkownika
        cur.execute(
            "SELECT g.name FROM user_books ub JOIN books b ON ub.book_id = b.id JOIN genres g ON b.genre_id = g.id WHERE ub.user_id = ?",
            (uid,),
        )
        book_genres = [row[0] for row in cur.fetchall()]

        fav_match = sum(1 for g in book_genres if g in fav_genres) if fav_genres else 0
        age_match = sum(1 for g in book_genres if g in age_genres)
        other_match = book_count - fav_match - age_match + min(fav_match, age_match)

        # Analiza biasu wyboru gatunków: ile książek pochodzi z ulubionych gatunków, ile z gatunków dopasowanych do wieku, a ile innych
        genre_bias_checks.append(
            {
                "user": username,
                "age": age,
                "age_category": cat,
                "favorite_genres": fav_genres,
                "age_based_genres": age_genres,
                "total_books": book_count,
                "books_from_favorites": fav_match,
                "books_from_age_group": age_match - min(fav_match, age_match),
                "books_other": book_count
                - fav_match
                - (age_match - min(fav_match, age_match)),
                "pct_favorite": (
                    round(100.0 * fav_match / book_count, 1) if book_count else 0
                ),
            }
        )

    # Podsumowanie wyników testu integracyjnego w formie czytelnej dla konsoli, z kluczowymi metrykami i przykładowymi danymi do weryfikacji poprawności działania symulacji i integracji z bazą danych
    out = {
        "pool_count": len(pool_all),
        "books_total": books_total,
        "books_with_openlibrary_id": books_with_pool,
        "activity_total": activity_total,
        "meta_last_activity": meta_val,
        "sample_books": [
            dict(zip(["id", "title", "openlibrary_id"], row)) for row in sample_books
        ],
        "logs_count": len(logs),
        "recent_activities": logs,
        "genre_selection_bias_samples": genre_bias_checks,
    }

    # Wyświetlenie wyników w czytelnym formacie konsolowym
    print("--- Podsumowanie integracji ---")
    print(f"Liczba pozycji w puli: {out['pool_count']}")
    print(f"Liczba książek w bazie: {out['books_total']}")
    print(f"Książki z openlibrary_id: {out['books_with_openlibrary_id']}")
    print(f"Liczba aktywności: {out['activity_total']}")
    print(f"Ostatnia aktywność w meta: {out['meta_last_activity']}")

    print("\nPrzykładowe książki:")
    for b in out["sample_books"]:
        print(f"  - {b['id']}: {b['title']} (openlibrary_id={b['openlibrary_id']})")

    print("\nOstatnie aktywności:")
    for log in out["recent_activities"]:
        print(f"  - {log}")

    print("\nPróbki biasu wyboru gatunków:")
    for s in out["genre_selection_bias_samples"]:
        print(
            f"  - {s['user']} (wiek {s['age']}, pct_favorite={s['pct_favorite']}%): ulubione={s['favorite_genres']}"
        )

    print(f"\nLiczba logów: {out['logs_count']}")

    conn.close()
    print("\nUruchomienie integracyjne zakończone.")


if __name__ == "__main__":
    run()
