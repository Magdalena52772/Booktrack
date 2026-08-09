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


def update_genre_stats(conn):
    """Aktualizacja globalnych statystyk popularności gatunków w bazie danych.
    Oblicza zasięg czytelniczy, średnie oceny oraz procentowy udział w przeczytanych stronach dla każdego gatunku.
    """
    cursor = conn.cursor()

    try:
        # Agregacja statystyk poprzez złączenie tabeli gatunków, katalogu książek oraz relacji użytkowników
        cursor.execute("""
            SELECT
                g.id,
                COUNT(DISTINCT ub.user_id) as readers,
                ROUND(IFNULL(AVG(CASE WHEN ub.status = 'finished' THEN ub.rating END), 0.0), 2) as avg_rating,
                COUNT(CASE WHEN ub.status = 'finished' THEN 1 END) as books_read
            FROM genres g
            LEFT JOIN books b ON g.id = b.genre_id
            LEFT JOIN user_books ub ON b.id = ub.book_id
            GROUP BY g.id
        """)
        stats = cursor.fetchall()

        total_finished = sum(row[3] for row in stats)

        updates = []
        for row in stats:
            g_id, readers, avg_rating, books_read = row
            if total_finished > 0:
                share = round((books_read / total_finished) * 100, 2)
            else:
                share = 0.0
            updates.append((readers, avg_rating, books_read, share, g_id))

        cursor.executemany(
            """
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """,
            updates,
        )

        conn.commit()
        print("[STATS] Batch update zakończony sukcesem.")
    except Exception as e:
        conn.rollback()
        print(f"[STATS ERROR] {e}")
        traceback.print_exc()
    finally:
        cursor.close()


def update_challenges_progress(conn):
    """Synchronizuje postępy w wyzwaniach z faktyczną aktywnością użytkowników.

    Sprawdza, ile książek użytkownik ukończył w czasie trwania swojego wyzwania.
    Automatycznie oznacza wyzwania jako 'finished', jeśli osiągnięto cel.
    Oznacza wyzwania jako 'failed', jeśli minął termin końcowy, a cel nie został spełniony.
    """
    cursor = conn.cursor()

    try:
        # Aktualizacja postępów na podstawie rekordów ukończenia przypisanych do tabeli user_books
        cursor.execute("""
            UPDATE challenges
            SET current_value = (
                SELECT COUNT(*) 
                FROM user_books 
                WHERE user_books.user_id = challenges.user_id 
                  AND user_books.status = 'finished'
                  AND user_books.finish_date BETWEEN challenges.start_date AND challenges.end_date
            )
            WHERE status = 'active' AND type = 'quantity'
        """)

        cursor.execute("""
            UPDATE challenges 
            SET status = 'finished' 
            WHERE status = 'active' AND current_value >= target_value
        """)

        cursor.execute("""
            UPDATE challenges 
            SET status = 'failed' 
            WHERE status = 'active' AND end_date < datetime('now')
        """)

        conn.commit()
        print("[CHALLENGES] Zsynchronizowano postępy i statusy wyzwań.")
    except Exception as e:
        conn.rollback()
        print(f"[CHALLENGES ERROR] {e}")
        traceback.print_exc()
    finally:
        cursor.close()


def update_all_user_streaks(cursor):
    """LOGIKA SERWISOWA: Przelicza i zapisuje streaki dla wszystkich użytkowników.

    Nowe konta (registered today) mają automatycznie 1 dzień streak bez liczenia.
    """
    cursor.execute("SELECT id, date_joined FROM users")
    users = cursor.fetchall()

    current_date = datetime.now().date()
    streak_updates = []

    for user in users:
        user_id = user["id"]
        date_joined_dt = DateHelper.to_datetime(user["date_joined"])
        date_joined = date_joined_dt.date() if date_joined_dt else current_date

        if date_joined == current_date:
            streak_updates.append((1, user_id))
            continue

        query = """
            SELECT DISTINCT date(timestamp) as activity_date
            FROM activity
            WHERE user_id = ?
            ORDER BY activity_date DESC
            LIMIT 100
        """
        rows = cursor.execute(query, (user_id,)).fetchall()

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

    cursor.executemany(
        "UPDATE users SET current_streak = ? WHERE id = ?", streak_updates
    )


def run_maintenance(conn):
    """Główny punkt wejścia do konserwacji danych Wywołuje wszystkie funkcje 
    aktualizujące statystyki i synchronizujące postępy w wyzwaniach.
    """
    cursor = conn.cursor()
    try:
        # Przeliczanie ogólnej liczby ukończonych książek z poziomu tabeli user_books
        cursor.execute("""
            UPDATE users 
            SET books_read = (
                SELECT COUNT(*) FROM user_books 
                WHERE user_books.user_id = users.id AND user_books.status = 'finished'
            )
        """)
        cursor.execute("""
            UPDATE users 
            SET pages_per_day = COALESCE(
                (
                    SELECT AVG(daily_sum) FROM (
                        SELECT SUM(pages_read) as daily_sum
                        FROM activity 
                        WHERE activity.user_id = users.id 
                          AND timestamp > date('now', '-30 days')
                        GROUP BY date(timestamp)
                    )
                ), 0.0
            )
            WHERE status != 'inactive'
        """)
        cursor.execute("UPDATE users SET pages_per_day = 0.0 WHERE status = 'inactive'")

        update_all_user_streaks(cursor)

        conn.commit()

        update_challenges_progress(conn)
        update_genre_stats(conn)

        stats_repo = StatsRepository(conn)
        global_avg = stats_repo.get_system_wide_ppd("month")

        print(
            f"Maintenance complete. Global Avg PPD (last 30 days): {global_avg:.2f}"
        )
        return global_avg
    except Exception as e:
        conn.rollback()
        print(f"Maintenance failed: {e}")
        traceback.print_exc()
        raise
    finally:
        cursor.close()
