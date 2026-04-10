"""Konfiguracja bazy danych i poświadczeń."""

from pathlib import Path

# Ścieżka do bazy danych i schematu SQL (3 poziomy w górę)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Ścieżki do bazy danych i schematu SQL
DB_PATH = BASE_DIR / "booktrack.db"
SCHEMA_PATH = BASE_DIR / "data" / "schema.sql"

# Zahashowane hasło do konta testowego 'test1234'
DJANGO_HASHED_PWD = 'pbkdf2_sha256$600000$u79vV3WpXzQ9$8p0/m/H7u0YvXmS7D5/V6eQzX7P8R9a0b1c2d3e4f5g='

# Hashed password for 'test1234'
DJANGO_HASHED_PWD = 'pbkdf2_sha256$600000$u79vV3WpXzQ9$8p0/m/H7u0YvXmS7D5/V6eQzX7P8R9a0b1c2d3e4f5g='
