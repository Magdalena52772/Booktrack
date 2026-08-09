import random
from datetime import datetime, timedelta
from data.config import (
    get_fake,
    ARCHETYPE_SETTINGS,
    SEASONAL_IMPACT,
    SIM_SETTINGS,
    AGE_BASED_GENRES,
    GENRES,
)
from data.services.generator_service import GeneratorService
from data.repositories.genre_repo import GenresRepository
from data.services.user_service import update_user_ppd
from data.data_generator.books import _inserted_row_id, _load_book_pool
from data.data_generator.openlib_api import get_book_live_or_fallback


def _get_val(obj, key, default=None):
    """Helper do bezpiecznego odczytu właściwości z obiektów, słowników oraz wierszy DB"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    elif hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except Exception:
        return default


# =================== GENEROWANIE AKTYWNOŚCI ===================
def generate_activity(conn, users, books):
    """
    Symuluje sesje czytania. Dla każdej książki cofa się w czasie od daty
    zakończenia i generuje sesje
    Uwzględnia archetypy, weekendy oraz sezonowość
    """
    cursor = conn.cursor()
    user_map = {_get_val(u, "id"): u for u in users}

    # Filtruje książki, które mają sesje zarejestrowane w aplikacji (nie dodane jako stary import)
    active_books = [b for b in books if _get_val(b, "added_by_generator") == 1]

    activity_data = []
    book_updates = []
    processed_pairs = set()

    for b in active_books:
        user_id = _get_val(b, "user_id")
        user = user_map.get(user_id)
        if not user:
            continue

        book_id = _get_val(b, "id")
        pair = (user_id, book_id)
        if pair in processed_pairs:
            continue
        processed_pairs.add(pair)

        cursor.execute("""
            SELECT EXISTS(
                SELECT 1
                FROM activity
                WHERE user_id = ?
                AND book_id = ?
            )
        """, (user_id, book_id))

        if cursor.fetchone()[0]:
            continue

        book_status = _get_val(b, "status")
        total_pages = _get_val(b, "total_pages", 300)

        # Pobieranie nazwy archetypu bezpośrednio z metadanych użytkownika
        arch_name = _get_val(user, "r_tier", "regular")
        arch_data = ARCHETYPE_SETTINGS[arch_name]
        dp_min, dp_max = arch_data["pages_range"]

        reg_dt = _get_val(b, "date_joined")
        if isinstance(reg_dt, str):
            from data.utils.helpers.date_helpers import DateHelper
            reg_dt = DateHelper.to_datetime(reg_dt)

        is_finished = book_status == "finished"
        is_inactive = _get_val(user, "status") == "inactive"
        user_last_activity = _get_val(user, "last_activity")
        
        if isinstance(user_last_activity, str):
            from data.utils.helpers.date_helpers import DateHelper
            user_last_activity = DateHelper.to_datetime(user_last_activity)

        # Wyznaczanie daty zakończenia (lub punktu odniesienia dla 'reading')
        if is_finished:
            end_limit = user_last_activity if is_inactive else datetime.now()

            # Zabezpieczenie przed ujemnym timedelta
            if end_limit <= reg_dt:
                end_limit = reg_dt + timedelta(hours=2)

            reading_days = max(
                3,
                total_pages // random.randint(15, 35)
            )

            finish_dt = min(
                end_limit,
                reg_dt + timedelta(days=reading_days)
            )
        else:
            finish_dt = user_last_activity if user_last_activity else datetime.now()

        # Pobranie aktualnego postępu użytkownika
        cursor.execute(
            """
            SELECT current_page
            FROM user_books
            WHERE user_id = ? AND book_id = ?
            """,
            (user_id, book_id),
        )

        row = cursor.fetchone()

        # Jeśli istnieje wpis user_books odczytaj current_page, w przeciwnym razie traktuj jako brak
        current_page = row[0] if row and row[0] is not None else None

        # Oblicza ile stron brakuje do pełnego przeczytania 
        # (z uwzględnieniem już istniejących sesji activity)
        cursor.execute("SELECT COALESCE(SUM(pages_read),0) FROM activity WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        existing_pages = int(cursor.fetchone()[0] or 0)
        target_pages = int(current_page or 0)

        # Ile brakuje (bierze pod uwagę już istniejące rekordy activity)
        remaining = max(0, int(target_pages) - existing_pages)

        current_date = finish_dt

        if remaining <= 0:
            continue

        # Generowanie sesji "wstecz" od daty zakończenia
        while remaining > 0:
            # Nie generuje sesji sprzed rejestracji.
            # Jeśli osiągnie granicę, dosynchronizuje brakujące strony na minimalnie późniejszym znaczniku.
            if current_date <= reg_dt:
                current_date = reg_dt + timedelta(minutes=1)

            month = current_date.month
            is_weekend = current_date.weekday() >= 5

            # --- LOGIKA Z PARAMETRAMI SYMULACJI ---
            seasonal_factor = SEASONAL_IMPACT.get(month, 1.0)

            # Weekend_boost_range z SIM_SETTINGS
            w_min, w_max = SIM_SETTINGS["weekend_boost_range"]
            weekend_multiplier = random.uniform(w_min, w_max) if is_weekend else 1.0

            # Bazowa liczba stron z archetypu
            base_pages = random.randint(dp_min, dp_max)
            pages_read = int(base_pages * seasonal_factor * weekend_multiplier)

            # Caps & safety (min 1 strona, nie więcej niż zostało)
            pages_read = max(1, min(pages_read, remaining))

            # Dodatkowe ograniczenie, aby nie przekroczyć pozostałych stron do przeczytania
            pages_read = min(pages_read, remaining)

            # Czas trwania sesji oparty na page_pace_range i min_session_time
            pace_min, pace_max = SIM_SETTINGS["page_pace_range"]
            session_min = int(pages_read * random.uniform(pace_min, pace_max))
            session_min = max(SIM_SETTINGS["min_session_time"], session_min)

            activity_data.append(
                (
                    user_id,
                    book_id,
                    current_date.strftime("%Y-%m-%d %H:%M:%S"),
                    pages_read,
                    session_min,
                )
            )

            remaining -= pages_read

            # Przerwa między sesjami zależna od archetypu (z SIM_SETTINGS)
            if arch_name == "power":
                gap_days = random.choice(SIM_SETTINGS["gap_power_user"])
            else:
                gap_days = random.randint(*SIM_SETTINGS["gap_standard"])

            gap_hours = random.randint(0, 23)
            gap_minutes = random.randint(0, 59)

            current_date -= timedelta(
                days=gap_days,
                hours=gap_hours,
                minutes=gap_minutes,
            )

        # Daty zakończenia dla tabeli user_books
        if is_finished:
            book_updates.append((finish_dt.strftime("%Y-%m-%d %H:%M:%S"), user_id, book_id))

    # BATCH INSERT dla sesji
    cursor.executemany(
        """
        INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
        VALUES (?, ?, ?, ?, ?)
    """,
        activity_data,
    )

    try:
        if activity_data:
            latest_ts = max(a[2] for a in activity_data)
            cursor.execute(
                "REPLACE INTO meta (k, v) VALUES ('last_activity', ?)", (latest_ts,)
            )
    except Exception:
        pass

    # Synchronizacja dat zakończenia trafia do user_books
    cursor.executemany(
        """
        UPDATE user_books 
        SET finish_date = ? 
        WHERE user_id = ? AND book_id = ?
        """, 
        book_updates
    )

    conn.commit()
    print(
        f"SUCCESS: Generated {len(activity_data)} sessions for {len(active_books)} books."
    )


# =========== SYMULACJA NOWYCH AKTYWNOŚCI (REAL-TIME) ============
def simulate_incremental_activity(conn, users_meta, books_meta, count=5):
    """
    Generowanie przyrostowej aktywności zwracającej listę zdarzeń dla UI (wywoływane przez QTimer w main).
    """
    cursor = conn.cursor()
    now = datetime.now()
    month = now.month
    logs = []

    # Pobranie mapy gatunków (DRY - z repozytorium)
    genre_map = GenresRepository.get_genre_map(cursor)

    # Ładowanie puli książek z Open Library (z cache) - będzie używane jako fallback
    pool_books, pool_books_by_genre = _load_book_pool()

    active_users = [u for u in users_meta if _get_val(u, "status") == "active"]
    if not active_users:
        return []

    for _ in range(count):
        user = random.choice(active_users)
        u_id = _get_val(user, "id")

        # pobiera username, jeśli nie ma to name
        user_name = _get_val(user, "username") or _get_val(user, "name") or f"User {u_id}"

        # Lista pomocnicza na logi z tej konkretnej iteracji dla jednego użytkownika
        user_iteration_logs = []

        # Sprawdza co użytkownik czyta (pobiera dane z tabeli łączącej user_books połączonej z katalogiem books)
        cursor.execute(
            """
            SELECT b.id, b.title, ub.current_page, b.total_pages 
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = ? AND ub.status = 'reading'
            """,
            (u_id,),
        )
        current_book = cursor.fetchone()

        is_new_book = False
        if not current_book:
            # --- SCENARIUSZ: NOWA KSIĄŻKA ---
            is_new_book = True
            bday = _get_val(user, "birth_date", "1990-01-01")
            if isinstance(bday, str):
                bday = datetime.strptime(bday, "%Y-%m-%d")

            age = now.year - bday.year
            cat = (
                "junior"
                if age < 18
                else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
            )
            pref_list = AGE_BASED_GENRES.get(cat, GENRES)

            # Pobieranie ulubionych gatunków użytkownika
            try:
                cursor.execute(
                    "SELECT g.name FROM user_favorite_genres ufg JOIN genres g ON g.id = ufg.genre_id WHERE ufg.user_id = ?",
                    (u_id,),
                )
                fav_rows = [r[0] for r in cursor.fetchall()]
            except Exception:
                fav_rows = []

            if fav_rows:
                genre_name = GeneratorService.generate_actual_reading_genre(
                    bday, fav_rows
                )
            else:
                genre_name = random.choice(pref_list)
            genre_id = genre_map.get(genre_name, 1)

            # Pobieranie książki z Open Library API (fallback do pool jeśli API fail)
            book_data = get_book_live_or_fallback(
                genre_name=genre_name,
                fallback_pool=(pool_books, pool_books_by_genre),
                force_api=True,
            )

            title = book_data["title"]
            total_p = book_data.get("page_count", 300)
            pool_id = book_data.get("openlibrary_id")
            author_name = book_data["authors"]
            source = book_data.get("source", "unknown")

            # Dodanie nowej książki do globalnego katalogu
            cursor.execute(
                """
                INSERT OR IGNORE INTO books (title, authors, openlibrary_id, genre_id, total_pages, added_by_generator)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (title, author_name, pool_id, genre_id, total_p),
            )

            book_id = _inserted_row_id(cursor)
            
            # Jeśli książka już istniała w bazie, lastrowid zwróci None, pobiera jej id
            if not book_id and pool_id:
                cursor.execute("SELECT id FROM books WHERE openlibrary_id = ?", (pool_id,))
                res = cursor.fetchone()
                if res:
                    book_id = res[0]

            curr_p = 0

            # Powiązanie tej książki z użytkownikiem w tabeli user_books
            if book_id:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_books (user_id, book_id, current_page, status)
                    VALUES (?, ?, 0, 'reading')
                    """,
                    (u_id, book_id),
                )

            # Zapamiętuje log o starcie, ale jeszcze nie dodaje do głównej listy
            user_iteration_logs.append(
                f"🆕 {user_name} started reading '{title}' ({source})"
            )
        else:
            book_id, title, curr_p, total_p = current_book

        if not book_id:
            continue

        # --- SCENARIUSZ: SESJA CZYTANIA ---
        r_tier = _get_val(user, "r_tier", "regular")
        is_weekend = now.weekday() >= 5

        pages_read, duration = GeneratorService.calculate_session_details(
            r_tier, is_weekend, total_p - curr_p
        )
        pages_read = max(
            1, min(int(pages_read * SEASONAL_IMPACT.get(month, 1.0)), total_p - curr_p)
        )
        duration = int(duration * SEASONAL_IMPACT.get(month, 1.0))

        # Oblicza ilość już przeczytanych stron dla tej pary użytkownik-książka
        cursor.execute("SELECT COALESCE(SUM(pages_read),0) FROM activity WHERE user_id = ? AND book_id = ?", (u_id, book_id))
        existing_pages = int(cursor.fetchone()[0] or 0)
        cap = max(0, total_p - existing_pages)
        pages_read = max(0, min(pages_read, cap))
        if pages_read <= 0:
            # Nic do dodania — oznacza jako finished jeśli trzeba i przechodzi dalej
            new_page = total_p
            is_done = True
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            new_page = curr_p + pages_read
            is_done = new_page >= total_p
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """
                INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
                VALUES (?, ?, ?, ?, ?)
            """,
                (u_id, book_id, timestamp, pages_read, duration),
            )

        # Aktualizacja książki, ale jeszcze nie dodaje logu o zakończeniu (bo może być więcej sesji)
        try:
            cursor.execute(
                "REPLACE INTO meta (k, v) VALUES ('last_activity', ?)", (timestamp,)
            )
        except Exception:
            # Tabela meta może nie istnieć, ignoruje jeśli jest problem
            pass

        if is_done:
            rating = random.randint(3, 5)
            cursor.execute(
                """
                UPDATE user_books 
                SET current_page = ?, status = 'finished', finish_date = ?, rating = ? 
                WHERE user_id = ? AND book_id = ?
                """,
                (total_p, timestamp, rating, u_id, book_id),
            )
            user_iteration_logs.append(
                f"🏆 {user_name} finished '{title}' ({rating}/5 ⭐)"
            )
        else:
            cursor.execute(
                """
                UPDATE user_books 
                SET current_page = ? 
                WHERE user_id = ? AND book_id = ?
                """, 
                (new_page, u_id, book_id)
            )
            user_iteration_logs.append(
                f"📖 {user_name} read {pages_read} pages of '{title}'"
            )

        # Dodaje logi użytkownika do głównej listy
        logs.extend(user_iteration_logs)

        # Aktualizacja PPD użytkownika
        update_user_ppd(cursor, u_id)

    conn.commit()
    return logs
