

from datetime import datetime
import random

from data.config.generator import AGE_BASED_GENRES, GENRES, RATING_SETTINGS
from data.config.seed import get_fake
from data.data_generator.books import _inserted_row_id, _load_book_pool
from data.repositories.genre_repo import GenresRepository
from data.services.generator_service import GeneratorService
from data.utils.helpers.date_helpers import DateHelper


def generate_books(conn, users):
    """
    Generowanie wolumenu książek przypisanych do użytkowników.
    Rozdziela dane na globalny katalog (books) oraz tabelę relacji (user_books).
    """
    cursor = conn.cursor()
    book_metadata = []

    pool_books, pool_books_by_genre = _load_book_pool()
    now = datetime.now()

    # Pobranie mapy gatunków z repozytorium (DRY)
    genre_map = GenresRepository.get_genre_map(cursor)

    for user in users:
        bd_raw = user.get("birth_date", "1990-01-01")
        reg_date_raw = user.get("date_joined", datetime.now().strftime("%Y-%m-%d"))
        
        bd = DateHelper.to_datetime(bd_raw)
        reg_date = DateHelper.to_datetime(reg_date_raw)

        # Dopasowanie puli gatunków do wieku użytkownika
        age = DateHelper.calculate_age(bd)
        cat = (
            "junior"
            if age < 18
            else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        )
        age_pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        # Preferencje użytkownika jeśli dostępne
        user_favs = user.get("favorite_genres") or []

        # Wyliczanie stażu i szansy na to, że książka jest starsza niż data dołączenia do apki
        days_on_platform = (now - reg_date).days
        import_ratio = max(0.2, 1.0 - (days_on_platform / 900))

        # Określenie liczby pozycji w bibliotece na podstawie danych profilowych
        total_finished = user.get("books_read", 2)
        currently_reading = random.randint(1, 2) if user["status"] == "active" else 0

        for i in range(total_finished + currently_reading):
            is_finished = i < total_finished
            status = "finished" if is_finished else "reading"

            # Losowanie gatunku
            if user_favs:
                genre_name = GeneratorService.generate_actual_reading_genre(bd, user_favs)
            else:
                genre_name = random.choice(age_pref_list)
            genre_id = genre_map.get(genre_name, 1)

            selected_pool = None
            if pool_books:
                genre_pool = pool_books_by_genre.get(genre_name, [])
                source_pool = genre_pool if genre_pool else pool_books
                selected_pool = random.choice(source_pool)

            if (
                selected_pool
                and isinstance(selected_pool.get("page_count"), int)
                and selected_pool.get("page_count") > 0
            ):
                total_pages = selected_pool.get("page_count")
            else:
                total_pages = random.randint(150, 600)

            # Losowanie oceny książki, jeśli jest ukończona i spełnia warunek prawdopodobieństwa
            rating = None
            if is_finished and random.random() < RATING_SETTINGS["review_probability"]:
                rating = random.choices(
                    RATING_SETTINGS["scores"], weights=RATING_SETTINGS["weights"]
                )[0]

            is_old_import = False if status == "reading" else (random.random() < import_ratio)

            if is_old_import:
                current_page = total_pages
                added_by_gen = 0
            else:
                added_by_gen = 1
                if is_finished:
                    current_page = total_pages
                else:
                    current_page = random.randint(1, total_pages - 1)

            if selected_pool:
                book_title = selected_pool.get("title") or f"{get_fake().word().title()} {get_fake().word().title()}"
                author = selected_pool.get("authors") or f"{get_fake().first_name()} {get_fake().last_name()}"
                pool_id = selected_pool.get("openlibrary_id")
            else:
                book_title = f"{get_fake().word().title()} {get_fake().word().title()}"
                author = f"{get_fake().first_name()} {get_fake().last_name()}"
                pool_id = None

            # Wstawienie pozycji do globalnego katalogu z ignorowaniem duplikatów API/JSON
            cursor.execute(
                """
                INSERT OR IGNORE INTO books (title, authors, openlibrary_id, genre_id, total_pages, added_by_generator)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (book_title, author, pool_id, genre_id, total_pages, added_by_gen),
            )
            book_id = _inserted_row_id(cursor)

            # Jeśli książka już istniała w bazie, pobiera jej ID
            if not book_id and pool_id:
                cursor.execute("SELECT id FROM books WHERE openlibrary_id = ?", (pool_id,))
                res = cursor.fetchone()
                if res:
                    book_id = res[0]

            # Fallback bezpieczeństwa na wypadek braku ID
            if not book_id:
                continue

            # Powiązanie książki z konkretnym użytkownikiem w tabeli user_books
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_books (user_id, book_id, current_page, status, rating)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user["id"], book_id, current_page, status, rating),
            )

            # Przechowywanie metadanych
            book_metadata.append(
                {
                    "id": book_id,
                    "user_id": user["id"],
                    "status": status,
                    "total_pages": total_pages,
                    "date_joined": reg_date,
                    "added_by_generator": added_by_gen,
                }
            )

    conn.commit()
    print(f"SUCCESS: Zindeksowano {len(book_metadata)} pozycji w katalogu globalnym i przypisano użytkownikom.")
    return book_metadata
