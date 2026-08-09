import random
from datetime import datetime, timedelta
from data.config import (
    GENRES,
    GENRE_WEIGHTS,
    ARCHETYPE_SETTINGS,
    SIX_MONTHS_INACTIVITY,
    DJANGO_HASHED_PWD,
)
from data.config.generator import INACTIVE_PROBABILITY
from data.config.seed import get_fake
from data.services.generator_service import GeneratorService
from data.repositories.genre_repo import GenresRepository
from data.services.user_service import get_archetype_name, get_user_identity

# =============== GENEROWANIE UŻYTKOWNIKÓW ===================


def generate_users(conn, count=1000):
    """Tworzy bazową tabelę użytkowników wraz z ich profilami czytelniczymi."""
    cursor = conn.cursor()
    now = datetime.now()

    # Inicjalizacja tabeli słownikowej gatunków
    for g in GENRES:
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (g,))
    conn.commit()

    # Mapowanie nazw gatunków na ich identyfikatory (DRY - z repozytorium)
    genre_map = GenresRepository.get_genre_map(cursor)

    # Przygotowanie losowego rozkładu statusów aktywności
    num_inactive = int(count * INACTIVE_PROBABILITY)
    statuses = ["inactive"] * num_inactive + ["active"] * (count - num_inactive)
    random.shuffle(statuses)

    temp_users_data = []

    for i in range(count):
        # Pobieranie danych tożsamości
        identity = get_user_identity(get_fake(), index=i)
        nickname = identity["nickname"]
        full_name = identity["full_name"]
        email = identity["email"]
        ext_id = 100000 + i
        status = statuses[i]

        # Obliczanie stażu konta
        register_date = get_fake().date_time_between(start_date="-2y", end_date="now")
        days_on_platform = (now - register_date).days
        account_years = max(0.1, days_on_platform / 365.25)

        # Losowanie archetypu na podstawie zdefiniowanych wag z konfiguracji 
        arch_name = random.choices(
            ["casual", "regular", "avid", "power"],
            weights=[
                ARCHETYPE_SETTINGS["casual"]["chance"],
                ARCHETYPE_SETTINGS["regular"]["chance"],
                ARCHETYPE_SETTINGS["avid"]["chance"],
                ARCHETYPE_SETTINGS["power"]["chance"]
            ]
        )[0]

        arch_cfg = ARCHETYPE_SETTINGS[arch_name]

        # Logika dla użytkowników nieaktywnych
        if status == "inactive":
            pages_per_day = 0.0
            reader_type = "casual"

            if days_on_platform > SIX_MONTHS_INACTIVITY:
                # Symulacja porzucenia aplikacji po pewnym czasie
                last_activity = get_fake().date_time_between(
                    start_date=register_date,
                    end_date=now - timedelta(days=SIX_MONTHS_INACTIVITY),
                )
                active_days = max(1, (last_activity - register_date).days)
                active_years = active_days / 365.25

                # Degradacja archetypu dla osób, które odeszły
                if random.random() < 0.5:
                    reader_type = "casual"
                    annual_limit = random.randint(3, 8)
                else:
                    reader_type = "regular"
                    annual_limit = random.randint(9, 15)

                books_read = max(1, int(active_years * annual_limit))
            else:
                # Wymuszenie statusu aktywnego dla kont nowszych niż limit nieaktywności
                status = "active"
                last_activity = now
                reader_type = arch_name
                books_read = max(
                    1, int(account_years * random.randint(*arch_cfg["annual_limit"]))
                )
                pages_per_day = 0.0

        # Logika dla użytkowników aktywnych
        if status == "active":
            # Ostatnia aktywność w ciągu ostatnich 7 dni
            act_start = max(register_date, now - timedelta(days=7))
            last_activity = get_fake().date_time_between(
                start_date=act_start, end_date="now"
            )
            reader_type = arch_name

            # Wyznaczanie statystyk na podstawie parametrów archetypu
            books_read = max(
                1, int(account_years * random.randint(*arch_cfg["annual_limit"]))
            )
            pages_per_day = 0.0

        birth_date_obj = GeneratorService.generate_birth_date()

        # Generowanie preferencji gatunkowych z uwzględnieniem wieku i biasu
        fav_genres = GeneratorService.generate_favorite_genres_for_birth(birth_date_obj)

        # Bezpieczne formatowanie daty urodzenia niezależnie od typu zwracanego obiektu
        if hasattr(birth_date_obj, "strftime"):
            birth_date_str = birth_date_obj.strftime("%Y-%m-%d")
        else:
            birth_date_str = str(birth_date_obj)

        # Przygotowanie danych do masowego zapisu (bulk insert)
        db_tuple = (
            DJANGO_HASHED_PWD,
            None,
            0,
            nickname,
            email,
            full_name,
            0,
            1,
            register_date.strftime("%Y-%m-%d %H:%M:%S"),
            ext_id,
            birth_date_str,
            status,
            last_activity.strftime("%Y-%m-%d %H:%M:%S"),
            reader_type,
            None,
            books_read,
            pages_per_day,
            0,
        )

        temp_users_data.append(
            {
                "db_tuple": db_tuple,
                "fav_genres": fav_genres,
                "meta": {
                    "id": None,
                    "nickname": nickname,
                    "date_joined": register_date,
                    "status": status,
                    "books_read": books_read,
                    "reader_type": reader_type,
                    "birth_date": birth_date_obj,
                    "r_tier": reader_type,
                    "last_activity": last_activity,
                },
            }
        )

    # Sortowanie chronologiczne i masowy zapis do bazy danych
    temp_users_data.sort(key=lambda u: u["meta"]["date_joined"])

    cursor.executemany(
        """
        INSERT INTO users (
            password, last_login, is_superuser, username, email, name,
            is_staff, is_active, date_joined, external_id, birth_date,
            status, last_activity, r_tier, cluster_group, books_read,
            pages_per_day, current_streak
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        [u["db_tuple"] for u in temp_users_data],
    )

    # Powiązanie wygenerowanych ID z ulubionymi gatunkami
    cursor.execute("SELECT id, username FROM users")
    db_users = {username: uid for uid, username in cursor.fetchall()}

    genre_relations = []
    final_meta_list = []

    for u in temp_users_data:
        u_name = u["meta"]["nickname"]
        if user_id := db_users.get(u_name):
            u["meta"]["id"] = user_id
            # Przeniesienie fav_genres do meta dla późniejszej analizy i testów
            u["meta"]["favorite_genres"] = u.get("fav_genres", [])
            final_meta_list.append(u["meta"])

            for g_name in u["fav_genres"]:
                if g_id := genre_map.get(g_name):
                    genre_relations.append((user_id, g_id))

    cursor.executemany(
        "INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)",
        genre_relations,
    )
    conn.commit()

    return final_meta_list


# ========== GENEROWANIE POJEDYNCZEGO UŻYTKOWNIKA (REAL-TIME) ===========

def generate_realtime_user(conn):
    """Symuluje rejestrację nowego użytkownika z zachowaniem unikalności danych."""
    cursor = conn.cursor()
    now = datetime.now()

    # Zapewnienie unikalności nazwy użytkownika poprzez losowanie nowej tożsamości przy kolizji
    while True:
        identity = get_user_identity(get_fake())
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (identity["nickname"],))
        if not cursor.fetchone():
            break

    # Pobieranie parametrów archetypu dla nowego konta
    arch_name = get_archetype_name()
    arch_cfg = ARCHETYPE_SETTINGS[arch_name]

    pages_per_day = 0.0
    books_read_count = random.randint(1, 2)
    register_date = now - timedelta(minutes=random.randint(5, 60))
    birth_date = GeneratorService.generate_birth_date()

    # Bezpieczne formatowanie daty urodzenia dla pojedynczego rekordu
    if hasattr(birth_date, "strftime"):
        birth_date_str = birth_date.strftime("%Y-%m-%d")
    else:
        birth_date_str = str(birth_date)

    # Zapewnienie unikalności identyfikatora zewnętrznego
    while True:
        external_id = random.randint(100000, 999999)
        cursor.execute("SELECT 1 FROM users WHERE external_id = ?", (external_id,))
        if not cursor.fetchone():
            break

    # Wstawienie rekordu nowego użytkownika
    cursor.execute(
        """
        INSERT INTO users (
            username, email, name, date_joined, status, birth_date,
            external_id, last_activity, pages_per_day, books_read,
            password, is_active, is_staff, is_superuser, current_streak, r_tier
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            identity["nickname"],
            identity["email"],
            identity["full_name"],
            register_date.strftime("%Y-%m-%d %H:%M:%S"),
            "active",
            birth_date_str,
            external_id,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            pages_per_day,
            books_read_count,
            DJANGO_HASHED_PWD,
            1,
            0,
            0,
            0,
            arch_name,
        ),
    )

    new_user_id = cursor.lastrowid

    # Przypisanie preferencji gatunkowych (z uwzględnieniem grupy wiekowej)
    selected_genres = set(
        GeneratorService.generate_favorite_genres_for_birth(birth_date)
    )
    genre_map = GenresRepository.get_genre_map(cursor)

    for g_name in selected_genres:
        if g_id := genre_map.get(g_name):
            cursor.execute(
                "INSERT OR IGNORE INTO user_favorite_genres (user_id, genre_id) VALUES (?, ?)",
                (new_user_id, g_id),
            )

    conn.commit()
    return new_user_id
