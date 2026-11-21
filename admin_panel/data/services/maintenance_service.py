"""
MAINTENANCE SERVICE
-------------------
Moduł odpowiada za spójność danych i przeliczanie statystyk w tle.
Główne zadania:
    Aktualizacja profili użytkowników (streaki, PPD, licznik książek).
    Synchronizacja postępów wyzwań czytelniczych.
    Przeliczanie globalnych trendów dla gatunków literackich.

Wywoływane cyklicznie przez timer aplikacji (w main.py).
"""

import traceback
from datetime import datetime, timedelta
from data.utils.helpers.date_helpers import DateHelper
from data.repositories.statistics_repo import StatsRepository
from data.repositories.maintenance_repo import MaintenanceRepository


def update_genre_stats(conn):
    """Aktualizacja globalnych statystyk popularności gatunków w bazie danych.
    Oblicza zasięg czytelniczy, średnie oceny oraz procentowy udział w przeczytanych stronach dla każdego gatunku.
    """
    repo = MaintenanceRepository(conn)

    try:
        stats = repo.get_genre_stats()

        total_finished = sum(row[3] for row in stats)

        updates = []
        for row in stats:
            g_id, readers, avg_rating, books_read = row
            if total_finished > 0:
                share = round((books_read / total_finished) * 100, 2)
            else:
                share = 0.0
            updates.append((readers, avg_rating, books_read, share, g_id))

        repo.update_genre_stats(updates)

        conn.commit()
        print("[STATS] Batch update zakończony sukcesem.")
    except Exception as e:
        conn.rollback()
        print(f"[STATS ERROR] {e}")
        traceback.print_exc()
    finally:
        pass


def update_challenges_progress(conn):
    """Synchronizuje postępy w wyzwaniach z faktyczną aktywnością użytkowników.

    Sprawdza, ile książek użytkownik ukończył w czasie trwania swojego wyzwania.
    Automatycznie oznacza wyzwania jako 'finished', jeśli osiągnięto cel.
    Oznacza wyzwania jako 'failed', jeśli minął termin końcowy, a cel nie został spełniony.
    """
    repo = MaintenanceRepository(conn)

    try:
        repo.sync_challenges()

        conn.commit()
        print("[CHALLENGES] Zsynchronizowano postępy i statusy wyzwań.")
    except Exception as e:
        conn.rollback()
        print(f"[CHALLENGES ERROR] {e}")
        traceback.print_exc()
    finally:
        pass


def update_all_user_streaks(cursor):
    """LOGIKA SERWISOWA: Przelicza i zapisuje streaki dla wszystkich użytkowników.

    Nowe konta (registered today) mają automatycznie 1 dzień streak bez liczenia.
    """
    repo = MaintenanceRepository(cursor.connection)
    users, activity_dates = repo.get_users_and_activity_dates()

    current_date = datetime.now().date()
    streak_updates = []

    for user in users:
        user_id = user["id"]
        date_joined_dt = DateHelper.to_datetime(user["date_joined"])
        date_joined = date_joined_dt.date() if date_joined_dt else current_date

        if date_joined == current_date:
            streak_updates.append((1, user_id))
            continue

        rows = activity_dates[user_id]

        streak = 0
        if rows:
            last_act_dt = DateHelper.to_datetime(rows[0][0])
            last_act = last_act_dt.date() if last_act_dt else current_date

            if (current_date - last_act).days <= 1:
                expected_date = last_act
                for row in rows:
                    act_date = DateHelper.to_datetime(row[0]).date()
                    if act_date == expected_date:
                        streak += 1
                        expected_date -= timedelta(days=1)
                    else:
                        break

        streak_updates.append((streak, user_id))

    repo.update_user_streaks(streak_updates)


def run_maintenance(conn):
    """Główny punkt wejścia do konserwacji danych Wywołuje wszystkie funkcje
    aktualizujące statystyki i synchronizujące postępy w wyzwaniach.
    """
    repo = MaintenanceRepository(conn)
    try:
        repo.sync_books_read()
        repo.sync_pages_per_day()

        update_all_user_streaks(conn.cursor())

        conn.commit()

        update_challenges_progress(conn)
        update_genre_stats(conn)

        stats_repo = StatsRepository(conn)
        global_avg = stats_repo.get_system_wide_ppd("month")

        print(f"Maintenance complete. Global Avg PPD (last 30 days): {global_avg:.2f}")
        return global_avg
    except Exception as e:
        conn.rollback()
        print(f"Maintenance failed: {e}")
        traceback.print_exc()
        raise
    finally:
        pass
