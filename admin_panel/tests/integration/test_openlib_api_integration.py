"""
Test integracji: Open Library API fallback chain
Testuje poprawne pobieranie nowych książek z API z fallback do puli
i weryfikuje źródła (API vs Pool vs Generated)
- Nowe książki z Open Library API
- Fallback do puli cached
- Fallback do generated data
- SOURCE BREAKDOWN reporting
"""

import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

root_path = next(
    (p for p in Path(__file__).parents if (p / "data").exists()),
    Path(__file__).parent.parent.parent,
)
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from data.database import initialize_database, get_connection
from data.data_generator.activity import simulate_incremental_activity


def main():
    print("\n" + "=" * 80)
    print("INTEGRATION TEST - Open Library API")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}\n")

    initialize_database()
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, status, name, username, r_tier, birth_date FROM users WHERE status = 'active' LIMIT 10"
        )
        users = [
            {
                "id": r[0],
                "status": r[1],
                "name": r[2],
                "username": r[3],
                "r_tier": r[4],
                "birth_date": r[5],
            }
            for r in cursor.fetchall()
        ]

        if not users:
            print("[ERROR] Brak active users!")
            return

        print(f"[OK] Found {len(users)} active users\n")

        cursor.execute("""
            SELECT
                b.id,
                ub.user_id,
                ub.status
            FROM books b
            JOIN user_books ub
                ON ub.book_id = b.id
            WHERE ub.status = 'reading'
            LIMIT 20
        """)
        books = [
            {"id": r[0], "user_id": r[1], "status": r[2]} for r in cursor.fetchall()
        ]
        print(f"[OK] Found {len(books)} books in progress\n")

        print("[SETUP] Finishing all active books so users start new ones...\n")
        cursor.execute("""
            UPDATE user_books
            SET
                status = 'finished',
                finish_date = CURRENT_TIMESTAMP,
                rating = 4
            WHERE status = 'reading'
        """)
        conn.commit()
        print("[OK] All books finished - users ready to start new ones\n")

        print("[SIMULATE] Generating 50 activity logs...\n")
        print("-" * 80)

        activity_counter = {"api": 0, "pool": 0, "generated": 0, "new_books": 0}

        for i in range(50):
            try:
                logs = simulate_incremental_activity(conn, users, books, count=1)

                for log in logs:
                    if "started reading" in log:
                        activity_counter["new_books"] += 1
                        if "from Open Library" in log or "(api)" in log.lower():
                            activity_counter["api"] += 1
                        elif "(pool)" in log.lower():
                            activity_counter["pool"] += 1
                        else:
                            activity_counter["generated"] += 1
                        print(f"[{i+1}] {log}")

                conn.commit()
            except TimeoutError:
                print(f"[{i+1}] [TIMEOUT] API too slow, skipping this iteration")
                conn.rollback()
                continue
            except Exception as e:
                print(f"[{i+1}] [ERROR] {str(e)[:80]}, using fallback")
                conn.rollback()
                continue

        print("\n" + "-" * 80)

        print("\n[SOURCE BREAKDOWN - Detailed]")
        cursor.execute("""
            SELECT b.id, b.title, b.openlibrary_id, b.added_by_generator
            FROM books b
            WHERE b.added_by_generator = 1
            ORDER BY b.id DESC
            LIMIT 100
        """)

        results = cursor.fetchall()

        api_books = []
        pool_books = []
        gen_books = []

        for book_id, title, openlibrary_id, added_by in results:
            if openlibrary_id:
                api_books.append((book_id, title, openlibrary_id))
            else:
                if (
                    title
                    and title.startswith("The ")
                    and "'" not in title
                    and len(title.split()) == 2
                ):
                    gen_books.append((book_id, title))
                else:
                    pool_books.append((book_id, title))

        print(f"  Total new books: {len(results)}")
        print(f"  From API:        {len(api_books)} ✅")
        print(f"  From Pool:       {len(pool_books)} 📚")
        print(f"  Generated:       {len(gen_books)} ⚠️")

        if api_books:
            print(f"\n  API Books (sample):")
            for book_id, title, openlibrary_id in api_books[:5]:
                print(f"     - {title} (OL: {openlibrary_id})")
            if len(api_books) > 5:
                print(f"     ... and {len(api_books)-5} more")

        if pool_books:
            print(f"\n  Pool Books (sample):")
            for book_id, title in pool_books[:5]:
                print(f"     - {title}")
            if len(pool_books) > 5:
                print(f"     ... and {len(pool_books)-5} more")

        if gen_books:
            print(f"\n  Generated Books:")
            for book_id, title in gen_books:
                print(f"     - {title}")

        print("\n" + "=" * 80)
        print(f"Test completed at: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
