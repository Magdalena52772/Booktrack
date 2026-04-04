import random
from datetime import datetime
from data.config import *

# =============== AKTUALIZACJA STATYSTYK GATUNKÓW ===================

def update_genre_stats(conn):
    """
    Przelicza globalne statystyki popularności gatunków w całym systemie.
    
    Oblicza:
    - Liczbę unikalnych czytelników na gatunek.
    - Średnią ocenę na podstawie realnych wpisów z tabeli 'books'.
    - Procentowy udział (share) danego gatunku w ogólnej liczbie przeczytanych książek.
    """
    cursor = conn.cursor()
    
    # 1. Pobranie ogólnej liczby ukończonych książek dla obliczenia udziałów (%)
    cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'finished'")
    res = cursor.fetchone()
    total_finished_books = res[0] if res and res[0] > 0 else 0

    # 2. Pobranie listy gatunków do przetworzenia
    cursor.execute("SELECT id, name FROM genres")
    genres = cursor.fetchall()

    genre_stats = []

    for genre_id, genre_name in genres:
        # A. Liczba unikalnych czytelników (kto przynajmniej raz dodał książkę z tego gatunku)
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM books WHERE genre_id = ?", (genre_id,))
        readers = cursor.fetchone()[0] or 0

        # B. Średnia ocena (tylko z ukończonych książek, które mają wystawioną ocenę)
        cursor.execute("""
            SELECT AVG(rating) FROM books 
            WHERE genre_id = ? AND status = 'finished' AND rating IS NOT NULL
        """, (genre_id,))
        avg_rating_res = cursor.fetchone()[0]
        avg_rating = round(avg_rating_res, 2) if avg_rating_res else 0.0

        # C. Liczba przeczytanych książek w tym gatunku
        cursor.execute("""
            SELECT COUNT(*) FROM books 
            WHERE genre_id = ? AND status = 'finished'
        """, (genre_id,))
        books_finished_count = cursor.fetchone()[0] or 0

        # D. UDZIAŁ: Procentowy wpływ gatunku na bibliotekę (zabezpieczenie przed dzieleniem przez zero)
        pct_share = 0.0
        if total_finished_books > 0:
            pct_share = round((books_finished_count / total_finished_books * 100), 2)

        genre_stats.append({
            'id': genre_id,
            'readers': readers,
            'avg_rating': avg_rating,
            'books_read': books_finished_count,
            'share': pct_share
        })

    # Sortowanie listy dla spójności (najpopularniejsze na górze)
    genre_stats.sort(key=lambda x: x['books_read'], reverse=True)

    # 3. Zapisanie przeliczonych statystyk z powrotem do tabeli 'genres'
    for stat in genre_stats:
        cursor.execute("""
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?, reading_time_share = ?
            WHERE id = ?
        """, (stat['readers'], stat['avg_rating'], stat['books_read'], stat['share'], stat['id']))

    conn.commit()
    
    # Reset ziarna losowości dla uniknięcia powtarzalnych wzorców w dalszej symulacji
    random.seed(datetime.now().timestamp())
    print(f"[STATS] Zaktualizowano statystyki dla {len(genres)} gatunków.")

    
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

    # 1. Synchronizacja 'current_value' na podstawie tabeli 'books'
    # Uwzględniamy tylko książki ukończone w widełkach czasowych wyzwania
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

    # 2. Masowa aktualizacja statusów na 'finished' (osiągnięcie celu)
    cursor.execute("""
        UPDATE challenges 
        SET status = 'finished' 
        WHERE status = 'active' AND current_value >= target_value
    """)

    # 3. Masowa aktualizacja statusów na 'failed' (przekroczenie terminu)
    cursor.execute("""
        UPDATE challenges 
        SET status = 'failed' 
        WHERE status = 'active' AND end_date < datetime('now')
    """)

    conn.commit()
    print("[CHALLENGES] Zsynchronizowano postępy i statusy wyzwań.")