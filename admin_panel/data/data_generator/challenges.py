import random
from datetime import datetime
from data.config import get_fake
from data.utils.helpers.date_helpers import DateHelper

# =================== GENEROWANIE WYZWAŃ ===================


def generate_challenges(conn, users, count_per_user=2):
    """Generuje losowe wyzwania czytelnicze ograniczone ramami bieżącego roku kalendarzowego.

    Postęp wyzwania (current_value) jest wyliczany na podstawie rzeczywistej liczby
    książek ukończonych przez użytkownika w bieżącym roku z tabeli user_books.
    """
    cursor = conn.cursor()
    challenges_list = []
    now = datetime.now()
    current_year = now.year

    # Współczynnik partycypacji - nie każdy użytkownik musi mieć wyzwania
    participation_chance = 0.4

    for user in users:
        # Obsługa ID oraz daty rejestracji użytkownika
        if isinstance(user, dict):
            user_id = user.get("id")
            reg_date = user.get("date_joined")
        else:
            user_id = user
            reg_date = None

        # Konwersja reg_date na obiekt datetime, jeśli jest stringiem
        if isinstance(reg_date, str):
            reg_date = DateHelper.to_datetime(reg_date)

        # Losowanie, czy użytkownik bierze udział w wyzwaniach
        if random.random() > participation_chance:
            continue

        # Pobranie liczby książek ukończonych w bieżącym roku
        cursor.execute(
            """
            SELECT COUNT(*) FROM user_books 
            WHERE user_id = ? 
              AND status = 'finished' 
              AND strftime('%Y', finish_date) = ?
            """,
            (user_id, str(current_year)),
        )
        real_finished_this_year = cursor.fetchone()[0]

        # Losuje liczbę wyzwań dla chętnego użytkownika
        num_to_gen = random.randint(1, count_per_user)

        for _ in range(num_to_gen):
            target_val = max(
                random.randint(5, 20), real_finished_this_year + random.randint(0, 3)
            )
            current_val = real_finished_this_year

            # Ustala datę rozpoczęcia wyzwania: jeśli użytkownik zarejestrował się w bieżącym roku, 
            # start jest losowany od daty rejestracji; w przeciwnym razie start jest losowany od początku roku.
            if reg_date and reg_date.year == current_year:
                year_start = reg_date
            else:
                year_start = datetime(current_year, 1, 1, 0, 0, 0)

            # Losuje start między wyznaczoną datą a momentem obecnym
            start_date = get_fake().date_time_between(
                start_date=year_start, end_date="now"
            )

            # Data zakończenia to zawsze koniec bieżącego roku
            end_date = datetime(current_year, 12, 31, 23, 59, 59)

            # Bezpieczne parsowanie obiektów dat zwracanych przez Faker do obiektów datetime
            start_date_dt = (
                DateHelper.to_datetime(start_date)
                if isinstance(start_date, str)
                else start_date
            )
            end_date_dt = (
                DateHelper.to_datetime(end_date)
                if isinstance(end_date, str)
                else end_date
            )

            # Generuje tytuł wyzwania w formacie "rok [Losowe słowo] Challenge"
            title = f"{current_year} {get_fake().word().capitalize()} Challenge"

            # Określa status wyzwania na podstawie bieżącej wartości i daty zakończenia
            if current_val >= target_val:
                status = "finished"
            elif end_date_dt < now:
                status = "failed"
            else:
                status = "active"

            # Dodaje wyzwanie do bazy danych
            try:
                cursor.execute(
                    """
                    INSERT INTO challenges (
                        user_id, title, type, target_value, current_value,
                        start_date, end_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        title,
                        "quantity",
                        target_val,
                        current_val,
                        start_date_dt.strftime("%Y-%m-%d") if start_date_dt else None,
                        end_date_dt.strftime("%Y-%m-%d") if end_date_dt else None,
                        status,
                    ),
                )

                challenges_list.append(
                    {"user_id": user_id, "title": title, "status": status}
                )
            except Exception as e:
                print(
                    f"[ERROR] Błąd przy dodawaniu wyzwania dla użytkownika {user_id}: {e}"
                )

    conn.commit()
    print(
        f"[SUCCESS] Wygenerowano {len(challenges_list)} wyzwań dla {len(users)} użytkowników."
    )

    return challenges_list