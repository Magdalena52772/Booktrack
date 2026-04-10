import sqlite3
from data.config import DB_PATH, SCHEMA_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    if not DB_PATH.exists():
        # jeśli bazy jeszcze nie ma, to ją utwórzy
        conn = get_connection()
        # Ścieżka do schema.sql (config.py)
        with open(SCHEMA_PATH, "r", encoding="utf8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print(f"Database created at: {DB_PATH}")
    else:
        print(f"Database already exists at: {DB_PATH}")