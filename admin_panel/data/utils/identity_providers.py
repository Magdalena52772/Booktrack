import random
from data.config import ARCHETYPE_SETTINGS

def slugify(text):
    """Zamienia polskie znaki na łacińskie (np. ą -> a) dla maili i loginów."""
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

    # Tworzymy nickname na podstawie slugify (małe litery, bez znaków specjalnych)
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