# Importy techniczne
from data.config import USER_COUNT
from data.database import get_connection

# Importy modułów generatora
from data.data_generator.users import generate_users
from data.data_generator.books import generate_books
from data.data_generator.activity import generate_activity
from data.data_generator.challenges import generate_challenges

from data.services.user_service import finalize_database_consistency

def run_data_generation():
    """
    Główny proces generowania danych: Users -> Books -> Challenges -> Activity -> Stats.
    """
    # Połączenie z bazą
    conn = get_connection()
    
    try:
        print(f"--- [START] Generowanie danych dla {USER_COUNT} użytkowników ---")

        # Generowanie użytkowników
        users = generate_users(conn, count=USER_COUNT)
        print(f"[OK] Wygenerowano {len(users)} użytkowników.")

        # Generowanie książek
        books = generate_books(conn, users)
        print(f"[OK] Wygenerowano wolumen książek.")

        # Generowanie wyzwań
        generate_challenges(conn, users)
        print(f"[OK] Wyzwania przypisane.")

        # Generowanie historycznej aktywności (sesje czytania)
        generate_activity(conn, users, books)
        print(f"[OK] Historia aktywności naniesiona.")

        # Aktualizacja statystyk gatunkowych i postępów w wyzwaniach
        print("[PROCESS] Finalizowanie spójności bazy danych...")
        finalize_database_consistency(conn) 
        
        conn.commit()
        print("\n--- [SUCCESS] Baza danych została w pełni zasilona i zsynchronizowana! ---")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Krytyczny błąd podczas generowania: {e}")
        raise e
    finally:
        conn.close()
        print("[INFO] Połączenie z bazą zamknięte.")

if __name__ == "__main__":
    run_data_generation()