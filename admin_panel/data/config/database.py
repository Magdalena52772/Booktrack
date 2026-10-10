"""Konfiguracja bazy danych i poświadczeń."""

from pathlib import Path

# Ścieżka do bazy danych i schematu SQL (3 poziomy w górę)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Ścieżki do bazy danych i schematu SQL
DB_PATH = BASE_DIR / "booktrack.db"
SCHEMA_PATH = BASE_DIR / "data" / "schema.sql"

# Poprawny hash Django używany przez generowane konta testowe.
DJANGO_HASHED_PWD = (
    "pbkdf2_sha256$1200000$E7oe6arSCV9SMgLpYtSXj0$Ci1DMQ8AErkiNBCcUc8Xw/R7R9qv7NgWc+05+bUpHEs="
)