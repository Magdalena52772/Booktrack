import random
from data.config import ARCHETYPE_SETTINGS
from data.services.maintenance_service import run_maintenance

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
    except:
    # Jeśli Fakerowi skończą się unikalne imiona, czyści cache i losuje dalej
        fake.unique.clear()
        f_name = fake.first_name()
        l_name = fake.last_name()

    # Tworzy nickname na podstawie slugify (małe litery, bez znaków specjalnych)
    clean_f = slugify(f_name)
    clean_l = slugify(l_name)
    
    # Dodaje suffix jeśli to konieczne dla unikalności
    suffix = index if index is not None else random.randint(10, 999)
    nickname = f"{clean_f}{clean_l}{suffix}"
    
    return {
        "first_name": f_name,
        "last_name": l_name,
        "full_name": f"{f_name} {l_name}",
        "nickname": nickname,
        "email": f"{nickname}@{fake.free_email_domain()}"
    }

def get_archetype_name(roll=None):
    """Zwraca nazwę archetypu na podstawie rzutu"""
    val = roll if roll is not None else random.random()
    for name, cfg in ARCHETYPE_SETTINGS.items():
        if val <= cfg["chance"]:
            return name
    return "regular"

def update_user_ppd(cursor, user_id):
    """Oblicza realne PPD na podstawie historii sesji i aktualizuje tabelę users."""
    cursor.execute("""
        SELECT 
            SUM(pages_read) as total_pages,
            COUNT(DISTINCT strftime('%Y-%m-%d', timestamp)) as active_days
        FROM activity 
        WHERE user_id = ?
    """, (user_id,))
    
    res = cursor.fetchone()
    if res and res[1] > 0:
        new_ppd = round(res[0] / res[1], 1)
        cursor.execute("UPDATE users SET pages_per_day = ? WHERE id = ?", (new_ppd, user_id))


def finalize_database_consistency(conn):
    """Główny punkt wejścia do synchronizacji danych po ciężkich operacjach SQL/API."""
    cursor = conn.cursor()
    
    # Uruchamia główny proces maintenance (Streaki, PPD, Książki)
    # to co faktycznie siedzi w activity logs
    run_maintenance(conn)
    
    # Synchronizacja licznika książek z tabeli BOOKS
    # Liczy faktyczne rekordy, żeby stan bazy był spójny
    cursor.execute("""
        UPDATE users 
        SET books_read = (
            SELECT COUNT(*) FROM books WHERE books.user_id = users.id
        )
    """)
    
    conn.commit()
    print("✅ Baza zsynchronizowana: Dane wynikają z rekordów aktywności.")