import random
from datetime import datetime
from data.config import get_fake

# =================== GENEROWANIE WYZWAŃ ===================

def generate_challenges(conn, users, count_per_user=2):
    """
    Generuje losowe wyzwania czytelnicze ograniczone ramami roku kalendarzowego.
    
    Logika:
    - Start: losowy moment między 1 stycznia a dzisiaj (max 6 miesięcy wstecz, ale w tym samym roku).
    - Koniec: zawsze 31 grudnia roku rozpoczęcia.
    - Status: automatycznie wyliczany na podstawie postępu i daty końcowej.
    """
    cursor = conn.cursor()
    challenges_list = []
    now = datetime.now()

    # Współczynnik partycypacji - nie każdy użytkownik musi mieć wyzwania (realizm Dashboardu)
    participation_chance = 0.4 

    for user in users:
        # Obsługa ID użytkownika (wyciągnięcie ze słownika meta lub bezpośrednio z ID)
        user_id = user.get('id') if isinstance(user, dict) else user
        
        # --- FILTR REALIZMU ---
        # Losuje, czy dany użytkownik w ogóle bierze udział w wyzwaniach
        if random.random() > participation_chance:
            continue

        # Losuje liczbę wyzwań dla chętnego użytkownika (od 1 do count_per_user)
        num_to_gen = random.randint(1, count_per_user)

        for _ in range(num_to_gen):
            # --- PARAMETRY ILOŚCIOWE ---
            # cel: 5 - 20 książek
            target_val = random.randint(5, 20)
            current_val = random.randint(0, target_val)
            
            # --- LOGIKA CZASOWA (ROK KALENDARZOWY) ---
            # Losuje start z ostatnich 6 miesięcy, ale nie poza bieżący rok
            start_date_raw = get_fake().date_time_between(start_date='-6M', end_date='now')
            
            # Ustawia start na wylosowany dzień, ale wymusza ten sam rok dla całego wyzwania
            if start_date_raw.year < now.year:
                start_date = datetime(now.year, 1, 1, random.randint(0, 23), random.randint(0, 59))
            else:
                start_date = start_date_raw

            # Data zakończenia to zawsze koniec roku, w którym wyzwanie się zaczęło
            end_date = datetime(start_date.year, 12, 31, 23, 59, 59)

            # --- KREACJA TYTUŁU ---
            # Tytuł zawiera rok i losowe słowo dla unikalności
            title = f"{start_date.year} {get_fake().word().capitalize()} Challenge"
            
            # --- DETERMINACJA STATUSU ---
            # Czy cel został osiągnięty?
            if current_val >= target_val:
                status = 'finished'
            # Czy termin już minął?
            elif end_date < now:
                status = 'failed'
            # W innym wypadku: Wyzwanie wciąż trwa
            else:
                status = 'active'

            # --- ZAPIS DO BAZY DANYCH ---
            try:
                cursor.execute("""
                    INSERT INTO challenges (
                        user_id, title, type, target_value, current_value,
                        start_date, end_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    title,
                    'quantity',  # Typ ilościowy
                    target_val,
                    current_val,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    status
                ))
                
                # Rejestracja wyzwania na liście do celów informacyjnych/logów
                challenges_list.append({
                    "user_id": user_id,
                    "title": title,
                    "status": status
                })
            except Exception as e:
                print(f"[ERROR] Błąd przy dodawaniu wyzwania dla użytkownika {user_id}: {e}")

    # Zatwierdzenie wszystkich rekordów w jednej transakcji
    conn.commit()
    print(f"[SUCCESS] Wygenerowano {len(challenges_list)} wyzwań dla {len(users)} użytkowników.")
    
    return challenges_list