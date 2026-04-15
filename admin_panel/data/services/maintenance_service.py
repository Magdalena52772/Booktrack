"""
MAINTENANCE SERVICE
-------------------
Ten moduł odpowiada za spójność danych i przeliczanie statystyk w tle.
Główne zadania:
1. Aktualizacja profili użytkowników (streaki, PPD, licznik książek).
2. Synchronizacja postępów wyzwań czytelniczych.
3. Przeliczanie globalnych trendów dla gatunków literackich.

Wywoływane cyklicznie przez timer aplikacji (w main.py).
"""

from datetime import datetime, timedelta
from data.utils.helpers.date_helpers import DateHelper
from data.config import USER_COUNT
from data.repositories.statistics_repo import StatsRepository

# =============== AKTUALIZACJA STATYSTYK GATUNKÓW ===================
def update_genre_stats(conn):
    """
    Aktualizacja globalnych statystyk popularności gatunków w bazie danych.
    Oblicza zasięg czytelniczy, średnie oceny oraz procentowy udział w rynku.
    """
    cursor = conn.cursor()

    # Oblicza wszystko jednym zapytaniem agregującym
    cursor.execute("""
        SELECT
            g.id,
            COUNT(DISTINCT b.user_id) as readers,
            ROUND(IFNULL(AVG(CASE WHEN b.status = 'finished' THEN b.rating END), 0.0), 2) as avg_rating,
            COUNT(CASE WHEN b.status = 'finished' THEN 1 END) as books_read
        FROM genres g
        LEFT JOIN books b ON g.id = b.genre_id
        GROUP BY g.id
    """)
    stats = cursor.fetchall()

    # Oblicza sumę wszystkich przeczytanych książek do udziału procentowego
    total_finished = sum(row[3] for row in stats) or 1

    # Przygotowanie danych do batch update
    try:
        updates = []
        for row in stats:
            g_id, readers, avg_rating, books_read = row
            share = round((books_read / total_finished) * 100, 2)
            updates.append((readers, avg_rating, books_read, share, g_id))

        # Batch update zamiast pętli
        cursor.executemany("""
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """, updates)

        conn.commit()
        print("[STATS] Batch update zakończony sukcesem.")
    except Exception as e:
        conn.rollback()
        print(f"[STATS ERROR] {e}")
    finally:
        cursor.close()

    
# ================== AKTUALIZACJA POSTĘPU WYZWAŃ ================= 

def update_challenges_progress(conn):
    """
    Synchronizuje postępy w wyzwaniach z faktyczną aktywnością użytkowników.
    
    Logika:
    1. Sprawdza, ile książek użytkownik ukończył w czasie trwania swojego wyzwania.
    2. Automatycznie oznacza wyzwania jako 'finished', jeśli osiągnięto cel.
    3. Oznacza wyzwania jako 'failed', jeśli minął termin końcowy, a cel nie został spełniony.
    """
    cursor = conn.cursor()

    # Synchronizacja 'current_value' na podstawie tabeli 'books'
    # Uwzględnia tylko książki ukończone w widełkach czasowych wyzwania
    cursor.execute("""
        UPDATE challenges
        SET current_value = (
            SELECT COUNT(*) 
            FROM books 
            WHERE books.user_id = challenges.user_id 
              AND books.status = 'finished'
              AND books.finish_date BETWEEN challenges.start_date AND challenges.end_date
        )
        WHERE status = 'active' AND type = 'quantity'
    """)

    # Masowa aktualizacja statusów na 'finished' (osiągnięcie celu)
    cursor.execute("""
        UPDATE challenges 
        SET status = 'finished' 
        WHERE status = 'active' AND current_value >= target_value
    """)

    # Masowa aktualizacja statusów na 'failed' (przekroczenie terminu)
    cursor.execute("""
        UPDATE challenges 
        SET status = 'failed' 
        WHERE status = 'active' AND end_date < datetime('now')
    """)

    conn.commit()
    print("[CHALLENGES] Zsynchronizowano postępy i statusy wyzwań.")

def update_all_user_streaks(cursor):
    """
    LOGIKA SERWISOWA: Przelicza i zapisuje streaki dla wszystkich użytkowników.
    Nowe konta (registered today) mają automatycznie 1 dzień streaki bez liczenia.
    """
    cursor.execute("SELECT id, date_joined FROM users")
    users = cursor.fetchall()

    current_date = datetime.now().date()

    for user in users:
        user_id = user['id']
        date_joined_dt = DateHelper.to_datetime(user['date_joined'])
        date_joined = date_joined_dt.date() if date_joined_dt else current_date

        # Nowe konto (registered today) - automatycznie 1 dzień
        if date_joined == current_date:
            cursor.execute("UPDATE users SET current_streak = ? WHERE id = ?", (1, user_id))
            continue

        # Logika obliczania streaka (limit 100 dni)
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

        cursor.execute("UPDATE users SET current_streak = ? WHERE id = ?", (streak, user_id))

def run_maintenance(conn):
    """Główny punkt wejścia do konserwacji danych."""
    cursor = conn.cursor()
    try:
        # Licznik przeczytanych książek
        cursor.execute("""
            UPDATE users 
            SET books_read = (
                SELECT COUNT(*) FROM books 
                WHERE books.user_id = users.id AND status = 'finished'
            )
        """)

        # Dynamiczne PPD (ostatnie 30 dni)
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

        # Streaki
        update_all_user_streaks(cursor)

        # Globalne KPI - SSOT: zawsze z ostatnich 30 dni (ta sama logika co dashboard i details)
        stats_repo = StatsRepository(conn)
        global_avg = stats_repo.get_system_wide_ppd("month")

        conn.commit()
        print(f"✅ Maintenance complete. Global Avg PPD (last 30 days): {global_avg:.2f}")
        return global_avg
    except Exception as e:
        conn.rollback()
        print(f"❌ Maintenance failed: {e}")
        raise