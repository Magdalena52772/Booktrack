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
import threading
from datetime import datetime

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from views.main_window import MainWindow
from worker import DatabaseWorker

from data.database import initialize_database, get_connection
from data.config import USER_COUNT

from data.data_generator.users import generate_users, generate_realtime_user
from data.data_generator.books import generate_books
from data.data_generator.activity import generate_activity, simulate_incremental_activity
from data.data_generator.challenges import generate_challenges

# ==================== PROFILING ====================
PROFILE_ENABLED = True
STARTUP_TIME = datetime.now()

def log_time(event: str):
    """Log timestamp dla performance profiling."""
    if PROFILE_ENABLED:
        elapsed = (datetime.now() - STARTUP_TIME).total_seconds()
        print(f"[TIMING] {elapsed:.2f}s | {event}")

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

def main():
    log_time("Script started")

    # Inicjalizacja bazy
    initialize_database()
    log_time("Database initialized")

    # Pobieranie połączenia
    conn = get_connection()
    log_time("DB connection established")

    app = QApplication(sys.argv)
    log_time("QApplication created")

    # Załadowanie matplotlib synchronicznie, żeby był gotowy zanim Dashboard go załaduje
    try:
        import matplotlib
        matplotlib.use('Qt5Agg')
        import matplotlib.pyplot as plt
        log_time("Matplotlib loaded synchronously")
    except Exception as e:
        print(f"[MATPLOTLIB] Load error: {e}")

    window = MainWindow(conn)
    log_time("MainWindow.__init__ completed")

    window.setWindowState(Qt.WindowMaximized)
    window.show()
    log_time("Window shown on screen")
    print("[UI] Okno pokazane - UI responsive!")

    # Uruchamia startup w oddzielnym wątku (bez blokowania UI)
    def run_startup_in_thread():
        """Startup w tle, nie blokuje UI - nowe połączenie dla wątku!"""
        from data.database import get_connection as get_db_connection
        from data.services.user_service import finalize_database_consistency

        # Nowe połączenie dla tego wątku (SQLite wymaga osobnych połączeń dla wątków)
        thread_conn = get_db_connection()

        try:
            # Sprawdzenie integralności bazy
            cursor = thread_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity'")
            if not cursor.fetchone():
                print("[CRITICAL] Tabela activity nie istnieje! Inicjalizacja wymuszona.")
                initialize_database()

            print("[STARTUP] Weryfikacja integralności danych...")
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]

            if user_count == 0:
                print("[INIT] Generowanie danych...")
                users_list = generate_users(thread_conn, count=USER_COUNT)
                books_list = generate_books(thread_conn, users_list)
                generate_challenges(thread_conn, users_list)
                generate_activity(thread_conn, users_list, books_list)
                finalize_database_consistency(thread_conn)
            else:
                print(f"[DATABASE] System gotowy. Liczba: {user_count}.")
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
                    new_id = generate_realtime_user(thread_conn)
                    cursor.execute("SELECT id, status, name, birth_date, date_joined, books_read FROM users WHERE id = ?", (new_id,))
                    row = cursor.fetchone()
                    if row:
                        u_data = {"id": row[0], "status": row[1], "name": row[2], "birth_date": row[3], "date_joined": row[4], "books_read": row[5]}
                        new_users.append(u_data)
                        print(f"[GROWTH] {datetime.now().strftime('%H:%M:%S')} | Nowy użytkownik: {u_data['name']}")

                if new_users:
                    generate_books(thread_conn, new_users)
                    generate_challenges(thread_conn, new_users)

                cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading'")
                books_in_progress = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in cursor.fetchall()]

                active_users = [u for u in (existing_users + new_users) if u["status"] == "active"]
                if active_users and books_in_progress:
                    act_count = random.randint(3, 8)
                    simulate_incremental_activity(thread_conn, active_users, books_in_progress, count=act_count)

            thread_conn.commit()
            cursor.close()
            log_time("Startup data generation completed")
            print("[STARTUP] Zakończone! UI odświeży się automatycznie.")
        except Exception as e:
            print(f"[STARTUP ERROR] {e}")
            thread_conn.rollback()
        finally:
            thread_conn.close()

    # Defer maintenance do DEPOIS niż Dashboard load
    def run_maintenance_later():
        """Uruchom maintenance po załadowaniu Dashboard'a."""
        from data.services.maintenance_service import run_maintenance
        from data.database import get_connection as get_db_connection

        print("[MAINTENANCE] Uruchamianie maintenance (bez blokowania Dashboard)...")
        maint_conn = get_db_connection()
        try:
            run_maintenance(maint_conn)
            maint_conn.commit()
            log_time("Startup sequence completed")
        finally:
            maint_conn.close()

    # Uruchamia startup w oddzielnym wątku, aby nie blokować UI
    startup_thread = threading.Thread(target=run_startup_in_thread, daemon=True)
    startup_thread.start()
    print("[UI] Startup w tle - UI RESPONSIVE!")


    def run_timer_update():
        """
        Cykliczna symulacja aktywności i odświeżanie statystyk globalnych.
        """
        from data.services.maintenance_service import run_maintenance, update_all_user_streaks

        timer_cursor = conn.cursor()
        try:
            # Codzienna aktualizacja streków o 19:00
            current_time = datetime.now()
            if current_time.hour == 19 and current_time.minute == 0:
                update_all_user_streaks(timer_cursor)
                conn.commit()
                print(f"[STREAKS] {current_time.strftime('%H:%M:%S')} | Daily streak recalculation completed.")

            # Określenie intensywności ruchu (pory dnia)
            hour = current_time.hour
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

                # Przelicza całą bazę po nowych logach
                run_maintenance(conn)
                conn.commit()

                # Log z dodanymi aktywnościami
                print(f"[LIVE] {datetime.now().strftime('%H:%M:%S')} | Added {len(new_logs)} activities:")
                for log in new_logs:
                    print(f"       {log}")

                # Aktualizacja widoku LiveFeed, jeśli jest otwarty
                if hasattr(window, 'view_config'):
                    for cfg in window.view_config.values():
                        if cfg["instance"] and cfg["instance"].__class__.__name__ == "LiveFeedView":
                            for log in new_logs:
                                cfg["instance"].add_log_entry(log)
                            break


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
    activity_timer.start(60000)  # 1 minuta

    # ==================== TIMER DLA UPDATE_GENRE_STATS ====================
    def run_genre_stats_worker():
        """Uruchamia DatabaseWorker dla update_genre_stats."""
        worker = DatabaseWorker("update_genre_stats", db_connection=conn)
        worker.finished.connect(lambda: print(f"[GENRES] {datetime.now().strftime('%H:%M:%S')} | Genre stats updated."))
        worker.error.connect(lambda err: print(f"[GENRES ERROR] {err}"))
        worker.start()

    def start_recurring_genre_timer():
        """Uruchamia recurring timer co 5 minut."""
        genre_timer = QTimer()
        genre_timer.timeout.connect(run_genre_stats_worker)
        genre_timer.start(300000)  # 5 minut = 300000ms
        return genre_timer

    # Delay 1 minuta, potem recurring co 5 minut
    QTimer.singleShot(60000, start_recurring_genre_timer)
    print("[GENRES] Timer zaplanowany: first run za 1 min, potem co 5 min")

    exit_code = app.exec() 
    conn.close()
    print("[EXIT] Połączenie z bazą zamknięte. Zamykanie panelu.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()