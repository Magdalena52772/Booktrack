import random
import json
from datetime import datetime
from pathlib import Path
from data.config import GENRES, AGE_BASED_GENRES, RATING_SETTINGS, get_fake
from data.services.generator_service import GeneratorService
from data.utils.helpers.date_helpers import DateHelper
from data.repositories.genre_repo import GenresRepository

POOL_FILE = Path(__file__).with_name("open_library_pool.json")

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
    Wykorzystuje mechanizm batch insert (executemany) dla optymalizacji wydajności bazy danych.
    """
    cursor = conn.cursor()
    all_books_data = [] # Dane do masowego wstawienia
    book_metadata = []  # Metadane potrzebne do późniejszej generacji aktywności
    
    pool_books, pool_books_by_genre = _load_book_pool()
    now = datetime.now()

    # Pobranie mapy gatunków z repozytorium (DRY - unika duplikatów)
    genre_map = GenresRepository.get_genre_map(cursor)

    for user in users:
        bd_raw = user.get('birth_date', '1990-01-01')
        reg_date_raw = user.get('date_joined', datetime.now().strftime("%Y-%m-%d"))
        # Konwersja dat na obiekty datetime dla poprawności obliczeń
        bd = DateHelper.to_datetime(bd_raw)
        reg_date = DateHelper.to_datetime(reg_date_raw)

        # Dopasowanie puli gatunków do wieku użytkownika (segmentacja demograficzna)
        age = DateHelper.calculate_age(bd)
        cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
        age_pref_list = AGE_BASED_GENRES.get(cat, GENRES)

        # Preferencje użytkownika jeśli dostępne
        user_favs = user.get('favorite_genres') or []
        
        # Wyliczanie stażu i szansy na to, że książka jest starsza niż data dołączenia do apki
        days_on_platform = (now - reg_date).days
        import_ratio = max(0.2, 1.0 - (days_on_platform / 900))

        # Określenie liczby pozycji w bibliotece na podstawie danych profilowych
        total_finished = user.get('books_read', 2)
        currently_reading = random.randint(1, 2) if user['status'] == 'active' else 0
        
        for i in range(total_finished + currently_reading):
            is_finished = i < total_finished
            status = 'finished' if is_finished else 'reading'
            
            # Losowanie gatunku: preferencja użytkownika, potem preferencje wiekowe
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

            if selected_pool and isinstance(selected_pool.get("page_count"), int) and selected_pool.get("page_count") > 0:
                total_pages = selected_pool.get("page_count")
            else:
                total_pages = random.randint(150, 600)
            
            # --- LOGIKA OCENY (RATING) ---
            rating = None
            if is_finished and random.random() < RATING_SETTINGS["review_probability"]:
                rating = random.choices(
                    RATING_SETTINGS["scores"], 
                    weights=RATING_SETTINGS["weights"]
                )[0]

            # Rozróżnienie książek nowo dodanych od zaimportowanej historii
            is_old_import = False if status == 'reading' else (random.random() < import_ratio)

            if is_old_import:
                # IMPORT: Książka została przeczytana "poza aplikacją"
                status = 'finished'  # Dla pewności, importuje tylko skończone jako stare
                current_page = total_pages
                added_by_gen = 0     # Generator aktywności to pominie -> PPD wyniesie 0.0
                rating = rating      # Rating zostaje, bo użytkownik mógł ocenić książkę przy imporcie
            else:
                # Książka czytana w trakcie symulacji
                added_by_gen = 1     
                if is_finished:
                    current_page = total_pages
                else:
                    # Losuje postęp dla książek w trakcie
                    current_page = random.randint(1, total_pages - 1)

            # Jeśli jest pula, próbuje ją wykorzystać, ale zawsze sprawdza poprawność danych (np. page_count)
            if selected_pool:
                book_title = selected_pool.get("title") or f"{get_fake().word().title()} {get_fake().word().title()}"
                author = selected_pool.get("authors") or f"{get_fake().first_name()} {get_fake().last_name()}"
                pool_id = selected_pool.get("openlibrary_id")
            else:
                book_title = f"{get_fake().word().title()} {get_fake().word().title()}"
                author = f"{get_fake().first_name()} {get_fake().last_name()}"
                pool_id = None
            
            all_books_data.append((
                user["id"], book_title, author, pool_id, genre_id,
                total_pages, current_page, status, added_by_gen, rating
            ))

            # Przechowywanie metadanych do wykorzystania w module activity.py
            book_metadata.append({
                "id": None, "user_id": user["id"], "status": status, 
                "total_pages": total_pages, "date_joined": reg_date, "added_by_generator": added_by_gen
            })

    # Batch insert - wstawianie wszystkich rekordów w jednej operacji
    cursor.executemany("""
        INSERT INTO books (user_id, title, authors, openlibrary_id, genre_id, total_pages, current_page, status, added_by_generator, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, all_books_data)
    
    # Przypisanie wygenerowanych przez bazę ID do listy metadanych
    last_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
    first_id = last_id - len(all_books_data) + 1
    for i, meta in enumerate(book_metadata): 
        meta["id"] = first_id + i

    conn.commit()
    print(f"SUCCESS: Zindeksowano {len(all_books_data)} pozycji w tabeli books.")
    return book_metadata