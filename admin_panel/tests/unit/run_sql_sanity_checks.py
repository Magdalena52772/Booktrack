import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.database import get_connection
from data.repositories.activity_repo import ActivityRepository
from data.repositories.user_repo import UserRepository


def run_checks():
    conn = get_connection()
    act_repo = ActivityRepository(conn)
    user_repo = UserRepository(conn)

    periods = ["week", "month", "year", "all"]

    print("SQL Sanity Checks")
    print("=================")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status='active'")
    active_users = cursor.fetchone()[0]
    print(f"Total users: {total_users}")
    print(f"Active users: {active_users}")

    for p in periods:
        unique_active = act_repo.get_unique_active_users(p)
        retention = act_repo.get_user_retention(p)
        churn = act_repo.get_user_churn(p)
        print(f"Period={p}: unique_active_in_activity={unique_active}, retention={retention}%, churn={churn}%")

        # Dodatkowa weryfikacja: czy liczba unikalnych aktywnych użytkowników z activity zgadza się z liczbą użytkowników o statusie 'active' w users (dla okresu "all")
        if p != 'all':
            from data.utils.time_periods import period_start
            from datetime import datetime, timedelta

            since_current = period_start(p)
            period_days = (datetime.now() - since_current).days or 1
            since_prev = since_current - timedelta(days=period_days)

            since_prev_str = since_prev.strftime("%Y-%m-%d %H:%M:%S")
            since_curr_str = since_current.strftime("%Y-%m-%d %H:%M:%S")

            cur = conn.cursor()
            # poprzednio aktywni użytkownicy (ids)
            cur.execute("SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp < ?", (since_prev_str, since_curr_str))
            prev = [r[0] for r in cur.fetchall()]
            prev_count = len(prev)

            # obecnie aktywni użytkownicy (ids)
            cur.execute("SELECT DISTINCT a.user_id FROM activity a JOIN users u ON a.user_id = u.id WHERE a.timestamp >= ? AND a.timestamp <= ?", (since_curr_str, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            curr = {r[0] for r in cur.fetchall()}

            retained = len([u for u in prev if u in curr])

            # Sprawdza, którzy z poprzednio aktywnych użytkowników nie są już aktywni (churned)
            if prev_count > 0:
                placeholders = ','.join(['?'] * prev_count)
                q = f"SELECT id FROM users WHERE id IN ({placeholders}) AND status != 'active'"
                cur.execute(q, prev)
                now_inactive = [r[0] for r in cur.fetchall()]
            else:
                now_inactive = []

            print(f"  Previous-period users: {prev_count}, Retained: {retained}, Now inactive: {len(now_inactive)}")
            if now_inactive:
                sample = now_inactive[:10]
                print(f"  Sample churned user ids: {sample}")

    conn.close()


if __name__ == '__main__':
    run_checks()
