"""
Test integracji: Live Feed Activity Logs
Testuje czy ostatnie logi aktywności są poprawnie pobierane
i wyświetlane w widoku Live Feed
"""
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

root_path = next((p for p in Path(__file__).parents if (p / "data").exists()), Path(__file__).parent.parent.parent)
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from data.database import initialize_database, get_connection
from data.data_generator.activity import simulate_incremental_activity
from data.repositories.activity_repo import ActivityRepository

def main():
    print("\n" + "="*80)
    print("INTEGRATION TEST - Live Feed Activity Logs")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}\n")

    initialize_database()
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, status, name, username, r_tier, birth_date FROM users WHERE status = 'active' LIMIT 10")
        users = [
            {
                "id": r[0],
                "status": r[1],
                "name": r[2],
                "username": r[3],
                "r_tier": r[4],
                "birth_date": r[5]
            }
            for r in cursor.fetchall()
        ]

        if not users:
            print("[ERROR] Brak active users!")
            return

        print(f"[OK] Found {len(users)} active users\n")

        cursor.execute("SELECT id, user_id, status FROM books WHERE status = 'reading' LIMIT 20")
        books = [{"id": r[0], "user_id": r[1], "status": r[2]} for r in cursor.fetchall()]
        print(f"[OK] Found {len(books)} books in progress\n")

        print("[SETUP] Finishing all active books so users start new ones...\n")
        cursor.execute("""
            UPDATE books SET status = 'finished', finish_date = CURRENT_TIMESTAMP, rating = 4
            WHERE status = 'reading'
        """)
        conn.commit()
        print("[OK] All books finished - users ready to start new ones\n")

        print("[SIMULATE] Generating 30 activity logs for LiveFeed...\n")
        print("-" * 80)

        log_count = 0
        for i in range(30):
            try:
                logs = simulate_incremental_activity(conn, users, books, count=1)
                if logs:
                    log_count += len(logs)
                    for log in logs:
                        print(f"[{i+1}] {log}")
                conn.commit()
            except TimeoutError:
                print(f"[{i+1}] [TIMEOUT] API too slow, skipping this iteration")
                conn.rollback()
                continue
            except Exception as e:
                print(f"[{i+1}] [ERROR] {str(e)[:80]}")
                conn.rollback()
                continue

        print("\n" + "-" * 80)

        print(f"\n[SUMMARY] Generated {log_count} activity logs")

        print("\n[LIVEFEED PREVIEW - Last 50 logs (as shown in UI)]")
        print("-" * 80)
        activity_repo = ActivityRepository(conn)
        logs = activity_repo.get_recent_activity_logs(limit=50)

        if logs:
            print(f"Total logs retrieved: {len(logs)}\n")
            for time_str, message in logs:
                print(f"[{time_str}] {message}")
        else:
            print("ℹ️ No activity logs found")

        print("\n[VERIFICATION]")
        cursor.execute("SELECT COUNT(*) FROM activity")
        total_activity = cursor.fetchone()[0]
        print(f"  Total activity records in DB: {total_activity}")

        cursor.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM activity")
        active_days = cursor.fetchone()[0]
        print(f"  Active days: {active_days}")

        print("\n" + "="*80)
        print(f"Test completed at: {datetime.now().strftime('%H:%M:%S')}")
        print("="*80 + "\n")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
