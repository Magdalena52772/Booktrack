"""
Book Track Admin Panel — Główny punkt wejścia aplikacji (Entry Point)

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
from datetime import datetime

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from views.main_window import MainWindow

from data.database import initialize_database, get_connection
from data.config import USER_COUNT
from data.repositories.user_repo import UserRepository

# Importy modułów generatora
from data.data_generator.users import generate_users, generate_realtime_user
from data.data_generator.books import generate_books
from data.data_generator.activity import generate_activity, simulate_incremental_activity
from data.data_generator.challenges import generate_challenges
from data.data_generator.stats import update_genre_stats


# Konfiguracja systemowa w celu poprawnego skalowania interfejsu użytkownika
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
# Poprawienie renderowania na monitorach o wysokiej rozdzielczości (DPI)
if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# Ustawienie katalogu roboczego na folder, w którym znajduje się main.py
basedir = os.path.dirname(os.path.abspath(__file__))
os.chdir(basedir)


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
        # SCENARIUSZ A: Pierwsze uruchomienie systemu i generowanie danych startowych
        users_list = generate_users(conn, count=USER_COUNT)
        books_list = generate_books(conn, users_list)
        generate_challenges(conn, users_list)
        generate_activity(conn, users_list, books_list)
        
        all_users = users_list
        books = books_list
        print(f"[INIT] Utworzono {len(all_users)} rekordów.")
    else:
        # SCENARIUSZ B: Uruchomienie przyrostowe i pobieranie danych z bazy
        print(f"\n[DATABASE] System gotowy. Wykryto {user_count} rekordów.")
        
        cursor.execute("""
            SELECT id, status, name, birth_date, date_joined, books_read, pages_per_day, last_activity 
            FROM users
        """)
        existing_users = [
            {
                "id": r[0], "status": r[1], "name": r[2], 
                "birth_date": r[3], "date_joined": r[4],
                "books_read": r[5],
                "pages_per_day": r[6],
                "last_activity": r[7]
            } for r in cursor.fetchall()
        ]

        # Dodawanie nowych użytkowników (Realtime Growth)
        new_users = []
        for _ in range(random.randint(0, 2)):
            new_id = generate_realtime_user(conn)
            cursor.execute("""
                SELECT id, status, name, birth_date, date_joined, books_read, pages_per_day, last_activity 
                FROM users WHERE id = ?
            """, (new_id,))
            row = cursor.fetchone()
            if row:
                u_data = {
                    "id": row[0], "status": row[1], "name": row[2], 
                    "birth_date": row[3], "date_joined": row[4],
                    "books_read": row[5],
                    "pages_per_day": row[6],
                    "last_activity": row[7]
                }
                new_users.append(u_data)
                print(f"[GROWTH] {datetime.now().strftime('%H:%M:%S')} | Dodano: {u_data['name']} (ID: {new_id})")

        if new_users:
            generate_books(conn, new_users)
            generate_challenges(conn, new_users)
            print(f"[GROWTH] Wygenerowano książki i wyzwania dla nowych kont.")
        
        all_users = existing_users + new_users
        
        cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
        books_in_progress = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in cursor.fetchall()]
        
        if [u for u in all_users if u["status"] == "active"] and books_in_progress:
            act_count = random.randint(3, 8)
            simulate_incremental_activity(conn, [u for u in all_users if u["status"] == "active"], books_in_progress, count=act_count)
            # Ponowna aktualizacja po aktywności startowej
            print(f"[STARTUP] Aktywność startowa i wyzwania zaktualizowane ({act_count} akcji).")

    # Agregacja danych i aktualizacja statystyk gatunkowych przed inicjalizacją warstwy prezentacji
    update_genre_stats(conn)
    

    # --- Synchronizacja streaków przed startem UI ---
    print("[INIT] Synchronizacja streaków użytkowników...")
    user_repo = UserRepository(conn)
    user_repo.update_all_streaks()

    # Inicjalizacja silnika aplikacji graficznej PySide6
    app = QApplication(sys.argv)
    
    # Utworzenie i wyświetlenie okna głównego panelu administracyjnego
    window = MainWindow(conn)
    
    # Wyświetlenie okna w trybie zmaksymalizowanym
    window.showMaximized()
    window.show()

    # ===================== SYMULACJA AKTYWNOŚCI CIĄGŁEJ (TIMED UPDATE) =====================
    def run_timer_update():
        """
        Symulacja aktywności z bezpiecznym zarządzaniem zasobami, wywoływana cyklicznie 
        przez QTimer, odpowiada za dynamikę bazy danych w czasie rzeczywistym.
        """
        # Inicjalizacja kursora dla operacji w tle
        timer_cursor = conn.cursor()
        try:
            current_hour = datetime.now().hour
            
            # --- LOGIKA NATĘŻENIA RUCHU ---
            if 18 <= current_hour <= 23: 
                base_activity = random.randint(10, 25)  # Szczyt aktywności (wieczór)
            elif 0 <= current_hour <= 6: 
                base_activity = random.randint(1, 5)    # Minimalny ruch (noc)
            else: 
                base_activity = random.randint(5, 12)   # Standardowa aktywność (dzień)

            # --- POBIERANIE DANYCH WEJŚCIOWYCH ---
            timer_cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
            current_books = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in timer_cursor.fetchall()]
            
            timer_cursor.execute("""
                SELECT id, status, name, birth_date, date_joined, books_read, pages_per_day, last_activity 
                FROM users 
                WHERE status = 'active'
            """)
            
            active_list = [
                {
                    "id": r[0], "status": r[1], "name": r[2], 
                    "birth_date": r[3], "date_joined": r[4],
                    "books_read": r[5],
                    "pages_per_day": r[6],
                    "last_activity": r[7]
                } for r in timer_cursor.fetchall()
            ]
            
            # --- WYKONANIE SYMULACJI ---
            if active_list and current_books:
                simulate_incremental_activity(conn, active_list, current_books, count=base_activity)
                conn.commit() # Zapisanie zmian wygenerowanych przez symulację
            
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"[LIVE UPDATE] {now_str} | Aktywność: {base_activity} akcji | Baza zaktualizowana.")
            
            # --- ODŚWIEŻANIE INTERFEJSU (UI) ---
            if hasattr(window, 'ui') and hasattr(window.ui, 'ContentArea'):
                current_widget = window.ui.ContentArea.currentWidget()
                
                # Iteruje po wartościach (które są słownikami konfiguracji)
                for cfg in window.view_config.values():
                    # Sprawdza, czy kontener tego widoku jest obecnie wyświetlany
                    if cfg["container"] == current_widget:
                        view = cfg["instance"]  # Pobiera stworzoną instancję widoku
                        
                        # Jeśli widok został już stworzony (nie jest None) i ma metodę load_view
                        if view and hasattr(view, "load_view"):
                            should_skip = False
                            
                            # Zabezpieczenie: nie odświeża, jeśli admin zaznaczył wiersz
                            if hasattr(view, "ui") and hasattr(view.ui, "table_users"):
                                if view.ui.table_users.selectedItems():
                                    should_skip = True
                            
                            if not should_skip:
                                view.load_view()
                                print(f"[LIVE UPDATE] UI: Widok {view.__class__.__name__} odświeżony.")
                            else:
                                print(f"[LIVE UPDATE] UI: Odświeżanie wstrzymane (użytkownik pracuje na danych).")
                        break # Znaleziono aktywny widok, nie sprawdza dalej
        except Exception as e:
            conn.rollback() # Cofnięcie zmian w razie błędu bazy
            print(f"[LIVE ERROR] Błąd podczas aktualizacji timerem: {e}")
        finally:
            timer_cursor.close()
                        
    # Konfiguracja i start timera (interwał 15 sekund)
    timer = QTimer()
    timer.timeout.connect(run_timer_update)
    timer.start(15000) 

    # Uruchomienie głównej pętli zdarzeń aplikacji
    exit_code = app.exec() 

    # Sprzątanie po zamknięciu okna
    conn.close()
    print("[EXIT] Database connection closed. Goodbye!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()