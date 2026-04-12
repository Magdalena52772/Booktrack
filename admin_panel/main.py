"""
Book Track Admin Panel — Główny punkt wejścia aplikacji (Entry Point)

Moduł integrujący wszystkie komponenty systemu administracyjnego. Odpowiada za:
* Inicjalizację cyklu życia aplikacji (QApplication) oraz głównego okna (MainWindow).
* Zarządzanie współdzielonym połączeniem z bazą danych SQLite (Dependency Injection).
* Koordynację nawigacji między widokami za pomocą mechanizmu QStackedWidget.
* Obsługę procesów w tle (QTimer) symulujących ruch użytkowników w czasie rzeczywistym.
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

from data.data_generator.users import generate_users, generate_realtime_user
from data.data_generator.books import generate_books
from data.data_generator.activity import generate_activity, simulate_incremental_activity
from data.data_generator.challenges import generate_challenges

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

def main():
    # Inicjalizacja bazy
    initialize_database()
    
    # Pobieranie połączenia
    conn = get_connection()
    
    app = QApplication(sys.argv)
    
    window = MainWindow(conn)
    window.setWindowState(Qt.WindowMaximized)
    window.show()

    if hasattr(window, 'view_config'):
        current_widget = window.ui.ContentArea.currentWidget()
        for cfg in window.view_config.values():
            if cfg["container"] == current_widget:
                if cfg["instance"] and hasattr(cfg["instance"], "load_view"):
                    cfg["instance"].load_view()
                    print("[UI] Wstępne ładowanie widoku zakończone.")
                break

    def run_startup():
        """
        Zarządzanie procesem inicjalizacji danych i przeliczania statystyk.
        Wykorzystanie lazy loadingu dla modułów analitycznych.
        """
        from data.services.user_service import finalize_database_consistency
        from data.services.maintenance_service import run_maintenance
        
        # Sprawdzenie integralności bazy i ewentualna inicjalizacja danych
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity'")
        if not cursor.fetchone():
            print("[CRITICAL] Tabela activity nie istnieje! Inicjalizacja wymuszona.")
            initialize_database()
        
        print("[STARTUP] Weryfikacja integralności danych...")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            print("[INIT] Generowanie danych...")
            users_list = generate_users(conn, count=USER_COUNT)
            books_list = generate_books(conn, users_list)
            generate_challenges(conn, users_list)
            generate_activity(conn, users_list, books_list)
            finalize_database_consistency(conn) 
        else:
            print(f"[DATABASE] System gotowy. Liczba: {user_count}.")
            # Jeśli baza już była, odświeża wszystko na start
            run_maintenance(conn)
            
            cursor.execute("SELECT id, status, name, username, birth_date, date_joined, books_read FROM users")
            existing_users = [
                {
                    "id": r[0], 
                    "status": r[1], 
                    "name": r[2], 
                    "username": r[3], 
                    "birth_date": r[4], 
                    "date_joined": r[5], 
                    "books_read": r[6]
                } for r in cursor.fetchall()
            ]

            new_users = []
            for _ in range(random.randint(0, 2)):
                new_id = generate_realtime_user(conn)
                cursor.execute("SELECT id, status, name, birth_date, date_joined, books_read FROM users WHERE id = ?", (new_id,))
                row = cursor.fetchone()
                if row:
                    u_data = {"id": row[0], "status": row[1], "name": row[2], "birth_date": row[3], "date_joined": row[4], "books_read": row[5]}
                    new_users.append(u_data)
                    print(f"[GROWTH] {datetime.now().strftime('%H:%M:%S')} | Nowy użytkownik: {u_data['name']}")

            if new_users:
                generate_books(conn, new_users)
                generate_challenges(conn, new_users)

            cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
            books_in_progress = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in cursor.fetchall()]
            
            active_users = [u for u in (existing_users + new_users) if u["status"] == "active"]
            if active_users and books_in_progress:
                act_count = random.randint(3, 8)
                simulate_incremental_activity(conn, active_users, books_in_progress, count=act_count)

        run_maintenance(conn) 
        conn.commit()
        cursor.close()

        if hasattr(window, 'view_config'):
            current_widget = window.ui.ContentArea.currentWidget()
            for cfg in window.view_config.values():
                if cfg["container"] == current_widget:
                    view = cfg["instance"]
                    if view and hasattr(view, "load_view"):
                        view.load_view()
                        print(f"[STARTUP] UI: Odświeżono widok {view.__class__.__name__}.")
                    break

    QTimer.singleShot(100, run_startup)


    def run_timer_update():
        """
        Cykliczna symulacja aktywności i odświeżanie statystyk globalnych.
        """
        from data.services.maintenance_service import run_maintenance
        
        timer_cursor = conn.cursor()
        try:
            # Określenie intensywności ruchu (pory dnia)
            hour = datetime.now().hour
            if 18 <= hour <= 23: base_activity = random.randint(10, 25)
            elif 0 <= hour <= 6: base_activity = random.randint(1, 5)
            else: base_activity = random.randint(5, 12)

            # Pobranie danych użytkowników
            timer_cursor.execute("SELECT id, status, name, username, r_tier, birth_date FROM users WHERE status = 'active'")
            active_list = [
                {
                    "id": r[0], 
                    "status": r[1], 
                    "name": r[2], 
                    "username": r[3],
                    "r_tier": r[4], 
                    "birth_date": r[5]
                } for r in timer_cursor.fetchall()
            ]

            # Pobranie książek w trakcie czytania
            timer_cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
            current_books = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in timer_cursor.fetchall()]
            
            if active_list and current_books:
                # Symuluje przyrostową aktywność i odświeża statystyki
                new_logs = simulate_incremental_activity(conn, active_list, current_books, count=base_activity)
                
                # Aktualizacja widoku LiveFeed, jeśli jest otwarty
                if hasattr(window, 'view_config'):
                    for cfg in window.view_config.values():
                        if cfg["instance"] and cfg["instance"].__class__.__name__ == "LiveFeedView":
                            for log in new_logs:
                                cfg["instance"].add_log_entry(log)
                            break

                # Przelicza całą bazę po nowych logach
                run_maintenance(conn) 
                conn.commit()
                print(f"[LIVE] {datetime.now().strftime('%H:%M:%S')} | Synchronizacja zakończona.")

            # Automatyczne odświeżanie widoku, jeśli użytkownik nic nie klika
            if hasattr(window, 'ui'):
                current_widget = window.ui.ContentArea.currentWidget()
                for cfg in window.view_config.values():
                    if cfg["container"] == current_widget:
                        view = cfg["instance"]
                        if view and hasattr(view, "load_view"):
                            # Zabezpieczenie przed odświeżaniem, gdy użytkownik pracuje na tabeli
                            should_skip = False
                            if hasattr(view, "ui") and hasattr(view.ui, "table_users"):
                                if view.ui.table_users.selectedItems():
                                    should_skip = True
                            
                            if not should_skip:
                                view.load_view()
                        break
        except Exception as e:
            conn.rollback()
            print(f"[LIVE ERROR] Błąd synchronizacji: {e}")
        finally:
            timer_cursor.close()

    activity_timer = QTimer()
    activity_timer.timeout.connect(run_timer_update)
    activity_timer.start(1500000) 

    exit_code = app.exec() 
    conn.close()
    print("[EXIT] Połączenie z bazą zamknięte. Zamykanie panelu.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()