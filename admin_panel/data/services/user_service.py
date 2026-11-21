import random
from data.config import ARCHETYPE_SETTINGS
from data.services.maintenance_service import run_maintenance
from data.repositories.maintenance_repo import MaintenanceRepository


def slugify(text):
    """Zamienia polskie znaki na łacińskie dla maili i loginów."""
    mapping = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    return text.translate(mapping).lower().replace(" ", "").replace("-", "")


def get_user_identity(fake, index=None):
    """Generuje spójne i unikalne dane tożsamości"""
    # Próba pobrania unikalnego imienia i nazwiska
    try:
        f_name = fake.unique.first_name()
        l_name = fake.unique.last_name()
    except BaseException:
        # Jeśli Fakerowi skończą się unikalne imiona, czyści cache i losuje dalej
        fake.unique.clear()
        f_name = fake.first_name()
        l_name = fake.last_name()

    # Tworzy nickname na podstawie slugify (małe litery, bez znaków specjalnych)
    clean_f = slugify(f_name)
    clean_l = slugify(l_name)

    suffix = index if index is not None else random.randint(10, 999)
    nickname = f"{clean_f}{clean_l}{suffix}"

    return {
        "first_name": f_name,
        "last_name": l_name,
        "full_name": f"{f_name} {l_name}",
        "nickname": nickname,
        "email": f"{nickname}@{fake.free_email_domain()}",
    }


def get_archetype_name(roll=None):
    """Zwraca nazwę archetypu na podstawie losowego rolla lub podanej wartości."""
    val = roll if roll is not None else random.random()
    for name, cfg in ARCHETYPE_SETTINGS.items():
        if val <= cfg["chance"]:
            return name
    return "regular"


def update_user_ppd(cursor, user_id):
    """Aktualizuje PPD przez repozytorium danych."""
    MaintenanceRepository(cursor.connection).update_user_ppd(user_id)


def finalize_database_consistency(conn):
    """Główny punkt wejścia do synchronizacji danych po ciężkich operacjach SQL/API."""
    # Uruchamia główny proces maintenance (Streaki, PPD, Książki)
    run_maintenance(conn)

    # Synchronizacja licznika książek z tabeli USER_BOOKS
    # Liczy faktycznie przeczytane pozycje na podstawie relacyji N:M
    MaintenanceRepository(conn).sync_books_read()

    conn.commit()
    print("Baza zsynchronizowana: Dane wynikają z rekordów aktywności.")
