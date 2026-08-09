"""
Buduje lokalną pulę książek z Open Library API (PL + ENG)
- 660 pozycji (60 na każdy z 11 gatunków)
- Filtrowanie: tylko książki z tytułami i autorami w alfabecie łacińskim
- Zapis do JSON z metadanymi (data wygenerowania, źródło, liczba pozycji)
"""

from __future__ import annotations

import json
import math
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import urlopen

# Dynamiczne ładowanie konfiguracji
try:
    from data.config import GENRES
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from data.config import GENRES

OUTPUT_FILE = Path(__file__).with_name("open_library_pool.json")
DEFAULT_TARGET_COUNT = 660
DEFAULT_TIMEOUT = 15
DEFAULT_SLEEP_MS = 250

GENRE_QUERY_ALIASES = {
    "Sci-Fi": "Science Fiction",
    "Childrens literature": "Children's literature",
}


def _is_latin_only(text: str) -> bool:
    # Sprawdza, czy tekst zawiera tylko znaki łacińskie (bez cyrylicy)
    return not bool(re.search(r"[\u0400-\u04FF]", text))


def _book_key(ol_key: str | None, title: str, authors_text: str) -> str:
    if ol_key:
        return ol_key
    return f"{title.strip().lower()}|{authors_text.strip().lower()}"


def _fetch_payload(url: str, timeout: int) -> dict | None:
    # Pobieranie danych z obsługą błędów i retry
    for attempt in range(3):
        try:
            with urlopen(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:  # Zbyt wiele żądań (rate limit)
                print(f"\n[429] Za szybko! Czeka 10s...")
                time.sleep(10)
            elif e.code >= 500:  # Błąd serwera
                time.sleep(2 * (attempt + 1))
            else:
                print(f"\n[HTTP {e.code}] Błąd dla URL: {url}")
                break
        except URLError as e:
            print(f"\n[Błąd sieci] {e.reason}. Próba {attempt + 1}/3...")
            time.sleep(2)
        except Exception as e:
            print(f"\n[Nieoczekiwany błąd] {e}")
            break
    return None


def _get_edition_title(edition_key: str | None) -> str | None:
    # Próba pozyskania tytułu, jeśli główny tytuł zawiera cyrylicę, 
    # ale może być dostępny w edycji łacińskiej
    if not edition_key:
        return None
    url = f"https://openlibrary.org/books/{edition_key}.json"
    data = _fetch_payload(url, timeout=5)
    if data and isinstance(data.get("title"), str):
        return data["title"].strip()
    return None


def _normalize_item(item: dict, genre: str) -> dict | None:
    # Standaryzacja, czyszczenie danych i filtracja alfabetu
    title = item.get("title", "")
    authors = item.get("author_name", ["Unknown"])
    authors_text = ", ".join(str(a) for a in authors)

    # Odrzucenie, jeśli tytuł jest zapisany cyrylicą (ale próba alternatywnego tytułu z edycji)
    if not _is_latin_only(title):
        edition_key = item.get("cover_edition_key")
        alt_title = _get_edition_title(edition_key)
        if alt_title and _is_latin_only(alt_title):
            title = alt_title
        else:
            return None

    # Odrzucenie, jeśli autorzy są zapisani cyrylicą
    if not _is_latin_only(authors_text):
        return None

    ol_key = item.get("key", "").replace("/works/", "")

    return {
        "openlibrary_id": ol_key or None,
        "title": title,
        "authors": authors_text,
        "page_count": item.get("number_of_pages_median") or 300,
        "genre_hint": genre,
    }


def main() -> None:
    genres = list(GENRES)
    target_count = DEFAULT_TARGET_COUNT
    per_genre_target = math.ceil(target_count / len(genres))

    books = []
    seen = set()

    print(f"Rozpoczyna pobieranie {target_count} pozycji z Open Library...")

    for genre in genres:
        genre_added = 0
        page = 1
        max_attempts = 20

        while genre_added < per_genre_target and page <= max_attempts:
            query = GENRE_QUERY_ALIASES.get(genre, genre)
            url = (
                "https://openlibrary.org/search.json"
                f"?subject={quote_plus(query)}"
                "&language=pol"
                "&fields=key,title,author_name,number_of_pages_median,cover_edition_key"
                f"&limit=100&page={page}"
            )

            payload = _fetch_payload(url, DEFAULT_TIMEOUT)
            if not payload or not payload.get("docs"):
                break

            for item in payload["docs"]:
                if genre_added >= per_genre_target:
                    break

                norm = _normalize_item(item, genre)
                if not norm:
                    continue

                key = _book_key(norm["openlibrary_id"], norm["title"], norm["authors"])
                if key not in seen:
                    seen.add(key)
                    books.append(norm)
                    genre_added += 1

            time.sleep(DEFAULT_SLEEP_MS / 1000)
            page += 1

        print(f"[GATUNEK] {genre:15} | Dodano: {genre_added:2} | Razem: {len(books)}")

    # Przygotowanie finalnej struktury danych
    payload_out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "openlibrary.org",
        "count": len(books),
        "books": books,
    }

    # Zapis do pliku JSON
    try:
        OUTPUT_FILE.write_text(
            json.dumps(payload_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nSukces! Pula książek zapisana w: {OUTPUT_FILE}")
    except Exception as e:
        print(f"\nBłąd podczas zapisu pliku: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika.")
        sys.exit(130)
