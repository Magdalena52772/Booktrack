# data/database.py
from pathlib import Path
import sqlite3

BASE = Path(__file__).parent
DB_PATH = BASE / "booktrack.db"
SCHEMA_PATH = BASE / "schema.sql"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # pozwala odczytywać wiersze jako słowniki
    return conn

def initialize_database():
    if not DB_PATH.exists():
        # jeśli bazy jeszcze nie ma, to ją utwórz
        conn = get_connection()
        with open(SCHEMA_PATH, "r", encoding="utf8") as f:
            conn.executescript(f.read())  # uruchamia schema.sql
        conn.commit()
        conn.close()
        print("Database created")
    else:
        print("Database already exists")
