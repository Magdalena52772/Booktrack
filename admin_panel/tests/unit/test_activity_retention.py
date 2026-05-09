import sqlite3
from data.repositories.activity_repo import ActivityRepository


def setup_db(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            status TEXT,
            date_joined TEXT
        )
    """)
    c.execute("""
        CREATE TABLE activity (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            pages_read INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()


def test_retention_counts_active_users_only():
    conn = sqlite3.connect(":memory:")
    setup_db(conn)
    cur = conn.cursor()
    # Two active users in users table
    cur.execute("INSERT INTO users (id, status, date_joined) VALUES (1, 'active', '2020-01-01 00:00:00')")
    cur.execute("INSERT INTO users (id, status, date_joined) VALUES (2, 'active', '2020-01-01 00:00:00')")
    # Activity from user 1 (exists) and user 3 (does not exist in users table)
    cur.execute("INSERT INTO activity (user_id, pages_read, timestamp) VALUES (1, 10, '2024-01-02 10:00:00')")
    cur.execute("INSERT INTO activity (user_id, pages_read, timestamp) VALUES (3, 20, '2024-01-02 11:00:00')")
    conn.commit()

    repo = ActivityRepository(conn)
    retention = repo.get_user_retention("all")
    assert retention == 50.0


def test_retention_no_users():
    conn = sqlite3.connect(":memory:")
    setup_db(conn)
    cur = conn.cursor()
    # no users, activity exists
    cur.execute("INSERT INTO activity (user_id, pages_read, timestamp) VALUES (1, 10, '2024-01-02 10:00:00')")
    conn.commit()

    repo = ActivityRepository(conn)
    assert repo.get_user_retention("all") == 0.0


def test_retention_clamped():
    conn = sqlite3.connect(":memory:")
    setup_db(conn)
    cur = conn.cursor()
    # Single active user in users table
    cur.execute("INSERT INTO users (id, status, date_joined) VALUES (1, 'active', '2020-01-01 00:00:00')")
    # Activity for user 1 (exists) and user 2 (not in users)
    cur.execute("INSERT INTO activity (user_id, pages_read, timestamp) VALUES (1, 10, '2024-01-02 10:00:00')")
    cur.execute("INSERT INTO activity (user_id, pages_read, timestamp) VALUES (2, 20, '2024-01-02 11:00:00')")
    conn.commit()

    repo = ActivityRepository(conn)
    retention = repo.get_user_retention("all")
    # With join, active_users == 1 and total_users == 1 => 100%
    assert retention == 100.0
