"""
BookTrack Admin Panel — Główny punkt wejścia aplikacji (Entry Point)

Moduł integrujący wszystkie komponenty systemu administracyjnego. Odpowiada za:
* Inicjalizację cyklu życia aplikacji (QApplication) oraz głównego okna (MainWindow).
* Zarządzanie współdzielonym połączeniem z bazą danych SQLite (Dependency Injection).
* Koordynację nawigacji między widokami (Dashboard, Genres, Activity, Reports) 
  za pomocą mechanizmu QStackedWidget.
* Obsługę procesów w tle (QTimer), w tym dynamicznego generatora aktywności 
  symulującego ruch użytkowników w czasie rzeczywistym.
* Zapewnienie integralności danych poprzez bezpieczne zamykanie sesji bazy danych 
  przy wyjściu z programu.
"""

import sys
import os
import random

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.main_window import MainWindow
from data.database import initialize_database, get_connection
from data.data_generator.generator import (
    generate_users,
    generate_books,
    generate_challenges,
    generate_activity,
    simulate_incremental_activity,
    update_genre_stats,
    generate_realtime_user,
    USER_COUNT,
    BOOK_COUNT,
    ACTIVITY_COUNT
)

# Konfiguracja systemowa w celu poprawnego skalowania interfejsu użytkownika
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


def main():
    # Inicjalizacja struktury bazy danych SQLite oraz ustanowienie połączenia
    initialize_database()
    conn = get_connection()
    cursor = conn.cursor()

    # Deklaracja list obiektów w celu zapewnienia ich dostępności dla mechanizmów symulacji
    all_users = []
    books = []

    # Weryfikacja obecności danych w systemie poprzez sprawdzenie liczby rekordów w tabeli użytkowników
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # SCENARIUSZ A: PIERWSZE URUCHOMIENIE SYSTEMU
        # Następuje generowanie pełnego zestawu danych syntetycznych (użytkownicy, książki, logi aktywności)
        users_list = generate_users(conn, count=USER_COUNT)
        books_list = generate_books(conn, users_list)
        generate_challenges(conn, users_list)
        generate_activity(conn, users_list, books_list)
        
        all_users = users_list
        books = books_list
        print(f"[INIT] System zainicjalizowany pomyślnie. Utworzono {len(all_users)} rekordów użytkowników.")
    else:
        # SCENARIUSZ B: URUCHOMIENIE PRZYROSTOWE
        # Pobierane są dane o istniejących rekordach w celu przeprowadzenia symulacji rozwoju bazy
        cursor.execute("SELECT id, status, age, name, external_id, books_read FROM users")
        existing_users = [
            {
                "id": row[0], 
                "status": row[1], 
                "age": row[2], 
                "name": row[3], 
                "external_id": row[4],
                "books_read": row[5]
            }
            for row in cursor.fetchall()
        ]

        # Symulacja dołączenia nowych użytkowników do systemu (zdarzenia losowe w czasie rzeczywistym)
        new_users = []
        for _ in range(random.randint(0, 3)):
            new_user_id = generate_realtime_user(conn)
            # DODANO: age do zapytania SELECT
            cursor.execute("SELECT id, status, name, books_read, age FROM users WHERE id = ?", (new_user_id,))
            row = cursor.fetchone()
            if row:
                new_users.append({
                    "id": row[0], 
                    "status": row[1], 
                    "name": row[2], 
                    "books_read": row[3],
                    "age": row[4] # Teraz klucz 'age' będzie dostępny
                })

        all_users = existing_users + new_users
        
        # Synchronizacja i weryfikacja rekordów książek przypisanych do użytkowników
        books = generate_books(conn, all_users)
        
        # Generowanie przyrostowych sesji czytelniczych odzwierciedlających aktywność między sesjami pracy panelu
        active_users = [u for u in all_users if u["status"] == "active"]
        simulate_incremental_activity(conn, active_users, books, count=random.randint(5, 15))
        
        print(f"[GROWTH] Synchronizacja danych zakończona. Łączna liczba użytkowników: {len(all_users)}.")

    # Agregacja danych i aktualizacja statystyk gatunkowych przed inicjalizacją warstwy prezentacji
    update_genre_stats(conn)

    # Inicjalizacja silnika aplikacji graficznej PyQt6
    app = QApplication(sys.argv)
    
    # Utworzenie i wyświetlenie okna głównego panelu administracyjnego
    window = MainWindow(conn)
    window.show()

    # ===================== SYMULACJA AKTYWNOŚCI CIĄGŁEJ (TIMED UPDATE) =====================
    def run_timer_update():
        """
        Funkcja wywoływana cyklicznie przez mechanizm QTimer. 
        Odpowiada za symulację bieżącej aktywności czytelniczej użytkowników 
        i wymuszenie odświeżenia widoków interfejsu.
        """
        active = [u for u in all_users if u["status"] == "active"]
        if active and books:
            # Losowanie liczby nowych aktywności w tej sesji
            count = random.randint(1, 4)
            
            # Rejestracja nowych zdarzeń czytelniczych w bazie danych
            simulate_incremental_activity(conn, active, books, count=count)
            
            # Informacja o postępie symulacji w konsoli
            print(f"[LIVE UPDATE] Wygenerowano {count} nowe aktywności czytelnicze.")
            
            # Jeśli instancja MainWindow implementuje metodę update_users_view, następuje odświeżenie danych
            # Pozwala to na wizualizację zmian statystycznych (np. strony na dzień) w trybie rzeczywistym
            if hasattr(window, 'update_users_view'):
                window.update_users_view()
                print("[LIVE UPDATE] Widok użytkowników został odświeżony.")

    # Konfiguracja timera systemowego (częstotliwość wywołań: raz na 60 sekund)
    timer = QTimer()
    timer.timeout.connect(run_timer_update)
    timer.start(60000) 

    # Uruchomienie głównej pętli zdarzeń środowiska PyQt6
    sys.exit(app.exec())

if __name__ == "__main__":
    main()