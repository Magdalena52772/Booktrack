import random
from datetime import datetime, timedelta
from data.config import get_fake, ARCHETYPE_SETTINGS, SEASONAL_IMPACT, SIM_SETTINGS, AGE_BASED_GENRES, GENRES
from data.services.generator_service import GeneratorService
from data.repositories.genre_repo import GenresRepository
from data.services.user_service import update_user_ppd
from data.data_generator.books import _load_book_pool
from data.data_generator.openlib_api import get_book_live_or_fallback


# =================== GENEROWANIE AKTYWNOŚCI ===================
def generate_activity(conn, users, books):
    """
    Symuluje sesje czytania. Dla każdej książki cofa się w czasie od daty 
    zakończenia i generuje sesje
    Uwzględnia archetypy, weekendy oraz sezonowość
    """
    cursor = conn.cursor()
    user_map = {u['id']: u for u in users}
    
    # Filtruje książki, które mają sesje zarejestrowane w aplikacji (nie dodane podczas rejestracji użytkownika)
    active_books = [b for b in books if b['added_by_generator'] == 1]
    
    activity_data = []
    book_updates = []

    for b in active_books:
        user = user_map.get(b['user_id'])
        if not user: continue
        
        # Pobieranie nazwy archetypu bezpośrednio z metadanych użytkownika
        arch_name = user.get('r_tier', 'regular')
        arch_data = ARCHETYPE_SETTINGS[arch_name]
        dp_min, dp_max = arch_data["pages_range"]
        
        reg_dt = b.get('date_joined')
        is_finished = b['status'] == 'finished'
        is_inactive = user['status'] == 'inactive'
        
        # Wyznaczanie daty zakończenia (lub punktu odniesienia dla 'reading')
        if is_finished:
            # Książka skończona między rejestracją a dziś (lub porzuceniem konta)
            end_limit = user['last_activity'] if is_inactive else datetime.now()
            
            # Zabezpieczenie przed ujemnym timedelta
            if end_limit <= reg_dt:
                end_limit = reg_dt + timedelta(hours=2)

            finish_dt = get_fake().date_time_between(
                start_date=reg_dt + timedelta(minutes=60), 
                end_date=end_limit
            )
        else:
            # Książka w trakcie - ostatnia sesja musi być spójna z ostatnią aktywnością
            finish_dt = user['last_activity']

        remaining = b['total_pages'] if is_finished else random.randint(1, b['total_pages'] - 1)
        current_date = finish_dt

        # Generowanie sesji "wstecz" od daty zakończenia
        while remaining > 0:
            # Nie generuje sesji sprzed rejestracji
            if current_date <= reg_dt:
                break

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
            
            # Czas trwania sesji oparty na page_pace_range i min_session_time
            pace_min, pace_max = SIM_SETTINGS["page_pace_range"]
            session_min = int(pages_read * random.uniform(pace_min, pace_max))
            session_min = max(SIM_SETTINGS["min_session_time"], session_min)

            activity_data.append((
                user['id'], b['id'], 
                current_date.strftime("%Y-%m-%d %H:%M:%S"), 
                pages_read, session_min
            ))

            remaining -= pages_read
            
            # Przerwa między sesjami zależna od archetypu (z SIM_SETTINGS)
            if arch_name == 'power':
                gap = random.choice(SIM_SETTINGS["gap_power_user"])
            else:
                gap = random.randint(*SIM_SETTINGS["gap_standard"])
                
            current_date -= timedelta(days=gap)

        # Zbiera daty zakończenia do późniejszego UPDATE
        if is_finished:
            book_updates.append((finish_dt.strftime("%Y-%m-%d %H:%M:%S"), b['id']))

    # BATCH INSERT dla wydajności (zamyka sesje w jednym ruchu)
    cursor.executemany("""
        INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
        VALUES (?, ?, ?, ?, ?)
    """, activity_data)

    # Aktualizacja meta.last_activity na podstawie najnowszej sesji (jeśli są nowe dane)
    try:
        if activity_data:
            # activity_data: (user_id, book_id, timestamp, pages_read, session_minutes)
            latest_ts = max(a[2] for a in activity_data)
            cursor.execute("REPLACE INTO meta (k, v) VALUES ('last_activity', ?)", (latest_ts,))
    except Exception:
        # Jeśli meta nie istnieje lub jest problem, ignoruje (będzie utworzone przy inicjalizacji DB)
        pass
    
    # Synchronizacja dat zakończenia w tabeli books
    cursor.executemany("UPDATE books SET finish_date = ? WHERE id = ?", book_updates)
    
    conn.commit()
    print(f"SUCCESS: Generated {len(activity_data)} sessions for {len(active_books)} books.")
    

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

    active_users = [u for u in users_meta if u['status'] == 'active']
    if not active_users: return []

    for _ in range(count):
        user = random.choice(active_users)
        
        # --- Pobiera username, jeśli nie ma to name ---
        user_name = user.get('username') or user.get('name') or f"User {user['id']}"
        
        # Lista pomocnicza na logi z tej konkretnej iteracji dla jednego użytkownika
        user_iteration_logs = []

        # Sprawdza co użytkownik czyta
        cursor.execute("SELECT id, title, current_page, total_pages FROM books WHERE user_id = ? AND status = 'reading'", (user['id'],))
        current_book = cursor.fetchone()
        
        is_new_book = False
        if not current_book:
            # --- SCENARIUSZ: NOWA KSIĄŻKA ---
            is_new_book = True
            bday = user.get('birth_date', '1990-01-01')
            if isinstance(bday, str): bday = datetime.strptime(bday, '%Y-%m-%d')
            
            age = (now.year - bday.year)
            cat = "junior" if age < 18 else "young_adult" if age <= 25 else "adult" if age <= 60 else "senior"
            pref_list = AGE_BASED_GENRES.get(cat, GENRES)
            
            # Pobieranie ulubionych gatunków użytkownika
            try:
                cursor.execute("SELECT g.name FROM user_favorite_genres ufg JOIN genres g ON g.id = ufg.genre_id WHERE ufg.user_id = ?", (user['id'],))
                fav_rows = [r[0] for r in cursor.fetchall()]
            except Exception:
                fav_rows = []

            if fav_rows:
                genre_name = GeneratorService.generate_actual_reading_genre(bday, fav_rows)
            else:
                genre_name = random.choice(pref_list)
            genre_id = genre_map.get(genre_name, 1)

            # Pobieranie książki z Open Library API (fallback do pool jeśli API fail)
            book_data = get_book_live_or_fallback(genre_name=genre_name, fallback_pool=(pool_books, pool_books_by_genre), force_api=True)
            
            title = book_data["title"]
            total_p = book_data.get("page_count", 300)
            pool_id = book_data.get("openlibrary_id")
            author_name = book_data["authors"]
            source = book_data.get("source", "unknown")

            cursor.execute("""
                INSERT INTO books (user_id, title, authors, openlibrary_id, genre_id, total_pages, current_page, status, added_by_generator)
                VALUES (?, ?, ?, ?, ?, ?, 0, 'reading', 1)
            """, (user['id'], title, author_name, pool_id, genre_id, total_p))
            
            book_id, curr_p, total_p = cursor.lastrowid, 0, total_p
            
            # Zapamiętuje log o starcie, ale jeszcze nie dodaje do głównej listy
            user_iteration_logs.append(f"🆕 {user_name} started reading '{title}' ({source})")
        else:
            book_id, title, curr_p, total_p = current_book

        # --- SCENARIUSZ: SESJA CZYTANIA ---
        r_tier = user.get('r_tier', 'regular')
        is_weekend = now.weekday() >= 5

        pages_read, duration = GeneratorService.calculate_session_details(r_tier, is_weekend, total_p - curr_p)
        pages_read = max(1, min(int(pages_read * SEASONAL_IMPACT.get(month, 1.0)), total_p - curr_p))
        duration = int(duration * SEASONAL_IMPACT.get(month, 1.0)) 

        new_page = curr_p + pages_read
        is_done = new_page >= total_p
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO activity (user_id, book_id, timestamp, pages_read, session_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user['id'], book_id, timestamp, pages_read, duration))

        # Aktualizacja książki, ale jeszcze nie dodaje logu o zakończeniu (bo może być więcej sesji)
        try:
            cursor.execute("REPLACE INTO meta (k, v) VALUES ('last_activity', ?)", (timestamp,))
        except Exception:
            # Tabela meta może nie istnieć, ignoruje jeśli jest problem (będzie utworzona przy inicjalizacji DB)
            pass

        if is_done:
            rating = random.randint(3, 5)
            cursor.execute("""
                UPDATE books SET current_page = ?, status = 'finished', finish_date = ?, rating = ? WHERE id = ?
            """, (total_p, timestamp, rating, book_id))
            user_iteration_logs.append(f"🏆 {user_name} finished '{title}' ({rating}/5 ⭐)")
        else:
            cursor.execute("UPDATE books SET current_page = ? WHERE id = ?", (new_page, book_id))
            user_iteration_logs.append(f"📖 {user_name} read {pages_read} pages of '{title}'")

        # --- Dodaje logi użytkownika do głównej listy ---
        logs.extend(user_iteration_logs)

        # Aktualizacja PPD użytkownika
        update_user_ppd(cursor, user['id']) 

    conn.commit()
    return logs