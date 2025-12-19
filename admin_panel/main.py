"""
BookTrack Admin Panel — entry point
"""

import sys
import os
import random
from datetime import datetime
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

# poprawia skalowanie bez używania usuniętych flag Qt5
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


def main():
    initialize_database()
    conn = get_connection()
    cursor = conn.cursor()

    all_users = []  # <-- inicjalizacja, zawsze istnieje

    # sprawdzenie, czy baza jest pusta
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # pełne generowanie startowe
        users = generate_users(conn, count=USER_COUNT)
        books = generate_books(conn, users, count=BOOK_COUNT)
        challenges = generate_challenges(conn, users)
        activity = generate_activity(conn, users, books)
        all_users = users
        print(f"[INIT] Generated {len(users)} users, {len(books)} books, {len(challenges)} challenges, {len(activity)} activity records")
    else:
        # baza istnieje – przyrost
        cursor.execute("SELECT id, status, age, name, external_id FROM users")
        existing_users = [
            {"id": row[0], "status": row[1], "age": row[2], "nickname": row[3], "external_id": row[4]}
            for row in cursor.fetchall()
        ]

        # dopisanie nowych userów w czasie rzeczywistym
        new_users_count = random.randint(0, 5)
        new_users = []
        for _ in range(new_users_count):
            new_user_id = generate_realtime_user(conn)
            cursor.execute(
                "SELECT id, status, register_date, last_activity FROM users WHERE id = ?",
                (new_user_id,)
            )
            row = cursor.fetchone()
            new_users.append({
                "id": row[0],
                "status": row[1],
                "register_date": datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S"),
                "last_activity": datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
            })

        all_users = existing_users + new_users

        # dopisanie nowych książek
        additional_books_count = random.randint(5, 15)
        books = generate_books(conn, all_users, count=additional_books_count)

        # dopisanie nowych wyzwań
        challenges = generate_challenges(conn, all_users, count_per_user=1)

        # aktywność tylko dla active users
        active_users = [u for u in all_users if u["status"] == "active"]
        activity = simulate_incremental_activity(conn, active_users, books, count=random.randint(5, 20))

        print(f"[GROWTH] Added {len(new_users)} new users, {len(books)} new books, {len(challenges)} new challenges, {len(activity)} activity records")

    # aktualizacja statystyk gatunków
    update_genre_stats(conn)

    # start PyQt
    app = QApplication(sys.argv)

    window = MainWindow(conn)
    window.show()

    # ===================== TIMER =====================
    # Drobne przyrosty aktywności co minutę (dla testów dynamicznych)
    timer = QTimer()
    timer.timeout.connect(
        lambda: simulate_incremental_activity(
            conn,
            [u for u in all_users if u["status"] == "active"],
            books,
            count=random.randint(2, 8)
        )
    )
    timer.start(60_000)  # co 60 sekund

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
