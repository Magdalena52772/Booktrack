import random
import json
from datetime import datetime
from pathlib import Path
from data.config import GENRES, AGE_BASED_GENRES, RATING_SETTINGS, get_fake
from data.services.generator_service import GeneratorService
from data.utils.helpers.date_helpers import DateHelper
from data.repositories.genre_repo import GenresRepository

POOL_FILE = Path(__file__).with_name("open_library_pool.json")


def _inserted_row_id(cursor):
    """Zwraca ID ostatnio wstawionego wiersza, jeśli został wstawiony dokładnie jeden wiersz."""
    return cursor.lastrowid if cursor.rowcount == 1 else None


def _load_book_pool():
    """Ładuje pulę książek z pliku JSON. Struktura danych jest
    zoptymalizowana pod kątem szybkiego dostępu do książek według gatunku.
    Zwraca listę wszystkich książek oraz słownik z książkami pogrupowanymi"""
    try:
        payload = json.loads(POOL_FILE.read_text(encoding="utf-8"))
        books = payload.get("books", [])
        if not isinstance(books, list):
            return [], {}

        by_genre = {}
        for book in books:
            if not isinstance(book, dict):
                continue
            genre_hint = book.get("genre_hint")
            if isinstance(genre_hint, str):
                by_genre.setdefault(genre_hint, []).append(book)

        return books, by_genre
    except Exception:
        return [], {}


# =================== GENEROWANIE KSIĄŻEK ===================
def generate_books(conn, users):
    """
    Generowanie wolumenu książek przypisanych do użytkowników.
    Bezpiecznie obsługuje obiekty User, sqlite3.Row oraz słowniki.
    """
    cursor = conn.cursor()
    book_metadata = []

    pool_books, pool_books_by_genre = _load_book_pool()
    now = datetime.now()

    # Pobranie mapy gatunków z repozytorium (DRY - unika duplikatów)
    genre_map = GenresRepository.get_genre_map(cursor)

    for user in users:
        # Helper do bezpiecznego wyciągania pól z obiektów i słowników
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            elif hasattr(obj, key):
                return getattr(obj, key)
            try:
                return obj[key]
            except Exception:
                return default

        # Wyciąganie danych niezależnie od formatu wejściowego
        user_id = get_val(user, "id")
        user_status = get_val(user, "status", "active")
        
        # Sprawdza books_read oraz alias books_count z bazy
        books_read = get_val(user, "books_read") or get_val(user, "books_count") or 2
        
        bd_raw = get_val(user, "birth_date", "1990-01-01")
        reg_date_raw = get_val(user, "date_joined", now.strftime("%Y-%m-%d"))
        
        # Konwersja dat na obiekty datetime dla poprawności obliczeń
        bd = DateHelper.to_datetime(bd_raw)
        reg_date = DateHelper.to_datetime(reg_date_raw)

        # Dopasowanie puli gatunków do wieku użytkownika (segmentacja demograficzna)
        age = DateHelper.calculate_age(bd)
        cat = (
            "junior"
            if age < 18
            else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        )
        age_pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        # Preferencje użytkownika
        user_favs = get_val(user, "favorite_genres", [])

        # Obliczenie współczynnika importu dla starszych kont 
        # (starsze konta mają większą szansę na import historii)
        days_on_platform = (now - reg_date).days
        import_ratio = max(0.2, 1.0 - (days_on_platform / 900))

        # Określenie liczby pozycji w bibliotece na podstawie danych profilowych
        total_finished = books_read
        currently_reading = random.randint(1, 2) if user_status == "active" else 0
        target_slots = total_finished + currently_reading

        cursor.execute("SELECT book_id FROM user_books WHERE user_id = ?", (user_id,))
        used_book_ids = {row[0] for row in cursor.fetchall()}

        slot_index = 0
        while slot_index < target_slots:
            is_finished = slot_index < total_finished
            status = "finished" if is_finished else "reading"
            inserted_for_slot = False

            # Losowanie gatunku: preferencja użytkownika, potem preferencje wiekowe
            for _ in range(8):
                if user_favs:
                    genre_name = GeneratorService.generate_actual_reading_genre(
                        bd, user_favs
                    )
                else:
                    genre_name = random.choice(age_pref_list)
                genre_id = genre_map.get(genre_name, 1)

                selected_pool = None
                genre_pool = pool_books_by_genre.get(genre_name, [])

                # Losowanie książki z puli gatunku, jeśli dostępna
                if genre_pool:
                    selected_pool = random.choice(genre_pool)

                if (
                    selected_pool
                    and isinstance(selected_pool.get("page_count"), int)
                    and selected_pool.get("page_count") > 0
                ):
                    total_pages = selected_pool.get("page_count")
                else:
                    total_pages = random.randint(150, 600)

                # Losowanie oceny książki tylko dla statusu "finished" i z określonym prawdopodobieństwem
                rating = None
                if is_finished and random.random() < RATING_SETTINGS["review_probability"]:
                    rating = random.choices(
                        RATING_SETTINGS["scores"], weights=RATING_SETTINGS["weights"]
                    )[0]

                # Rozróżnienie książek nowo dodanych od zaimportowanej historii
                is_old_import = (
                    False if status == "reading" else (random.random() < import_ratio)
                )

                if is_old_import:
                    current_page = total_pages
                    added_by_gen = 0
                else:
                    added_by_gen = 1
                    if is_finished:
                        current_page = total_pages
                    else:
                        current_page = random.randint(1, total_pages - 1)

                if selected_pool and genre_pool:
                    book_title = selected_pool.get("title") or f"{get_fake().word().title()} {get_fake().word().title()}"
                    author = selected_pool.get("authors") or f"{get_fake().first_name()} {get_fake().last_name()}"
                    pool_id = selected_pool.get("openlibrary_id")
                else:
                    book_title = f"{get_fake().word().title()} {get_fake().word().title()}"
                    author = f"{get_fake().first_name()} {get_fake().last_name()}"
                    pool_id = None

                # Zapis do globalnego słownika książek z ignorowaniem duplikatów z puli JSON
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO books (title, authors, openlibrary_id, genre_id, total_pages, added_by_generator)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (book_title, author, pool_id, genre_id, total_pages, added_by_gen),
                )
                book_id = _inserted_row_id(cursor)

                # Jeśli książka już była w bazie, pobiera jej istniejące ID oraz właściwy genre_id
                if not book_id and pool_id:
                    cursor.execute("SELECT id, genre_id FROM books WHERE openlibrary_id = ?", (pool_id,))
                    res = cursor.fetchone()
                    if res:
                        book_id = res[0]
                        genre_id = res[1]

                # Fallback na wypadek braku ID (np. błąd bazy)
                if not book_id or book_id in used_book_ids:
                    continue

                # Pobranie canonical_total_pages z bazy, aby uniknąć niespójności między user_books a books
                cursor.execute("SELECT total_pages FROM books WHERE id = ?", (book_id,))
                db_book_row = cursor.fetchone()
                canonical_total_pages = int(db_book_row[0]) if db_book_row and db_book_row[0] else int(total_pages)

                if status == "finished":
                    current_page = canonical_total_pages
                else:
                    max_reading_page = max(0, canonical_total_pages - 1)
                    current_page = min(max(0, int(current_page)), max_reading_page)

                # Zapis powiązania użytkownika z książką (N:M) - OR IGNORE chroni przed duplikatem pary
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_books (user_id, book_id, current_page, status, rating)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, book_id, current_page, status, rating),
                )

                # Jeśli relacja nie została utworzona (duplikat user_id+book_id), spróbuje inną książkę.
                if cursor.rowcount == 0:
                    continue

                used_book_ids.add(book_id)
                book_metadata.append(
                    {
                        "id": book_id,
                        "user_id": user_id,
                        "status": status,
                        "total_pages": canonical_total_pages,
                        "date_joined": reg_date,
                        "added_by_generator": added_by_gen,
                    }
                )
                inserted_for_slot = True
                break

            slot_index += 1

        # Aktywny użytkownik powinien mieć przynajmniej jedną książkę "reading".
        cursor.execute(
            "SELECT COUNT(*) FROM user_books WHERE user_id = ? AND status = 'reading'",
            (user_id,),
        )
        reading_count = cursor.fetchone()[0]
        if user_status == "active" and reading_count == 0:
            fallback_genre = random.choice(user_favs or age_pref_list)
            fallback_genre_id = genre_map.get(fallback_genre, 1)
            fallback_total_pages = random.randint(180, 550)
            fallback_title = f"{get_fake().word().title()} {get_fake().word().title()}"
            fallback_author = f"{get_fake().first_name()} {get_fake().last_name()}"
            cursor.execute(
                """
                INSERT INTO books (title, authors, openlibrary_id, genre_id, total_pages, added_by_generator)
                VALUES (?, ?, NULL, ?, ?, 1)
                """,
                (fallback_title, fallback_author, fallback_genre_id, fallback_total_pages),
            )
            fallback_book_id = cursor.lastrowid
            fallback_current_page = random.randint(1, fallback_total_pages - 1)
            cursor.execute(
                """
                INSERT INTO user_books (user_id, book_id, current_page, status, rating)
                VALUES (?, ?, ?, 'reading', NULL)
                """,
                (user_id, fallback_book_id, fallback_current_page),
            )
            book_metadata.append(
                {
                    "id": fallback_book_id,
                    "user_id": user_id,
                    "status": "reading",
                    "total_pages": fallback_total_pages,
                    "date_joined": reg_date,
                    "added_by_generator": 1,
                }
            )

    conn.commit()
    print(f"SUCCESS: Zindeksowano {len(book_metadata)} pozycji w katalogu globalnym i przypisano użytkownikom.")
    return book_metadata
