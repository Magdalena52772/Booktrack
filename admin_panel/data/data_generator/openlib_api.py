"""
Moduł odpowiedzialny za integrację z Open Library API
w celu pozyskiwania rzeczywistych danych o książkach
"""
import requests
import random
import time
from data.config import GENRES

# API endpoints i ustawienia
OPENLIB_SEARCH_URL = "https://openlibrary.org/search.json"
API_TIMEOUT = 10  # 10 sekund na odpowiedź API
MAX_RETRIES = 5  # 5 prób przed fallback
API_VERIFY_SSL = True  # Włącz weryfikację SSL
RETRY_DELAY = 0.5  # Delay między retries


def fetch_book_from_api(genre_name: str = None, fallback_pool=None):
    """
    Pobiera książkę z Open Library API na podstawie gatunku.
    W przypadku błędu lub braku wyników, zwraca None.
    Retry logic z exponential backoff: próbuje MAX_RETRIES razy przed zwróceniem None.
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Jeśli jest gatunek, używa go jako zapytania, w przeciwnym razie losowy gatunek z konfiguracji
            query = genre_name if genre_name else random.choice(GENRES)

            params = {
                "q": query,
                "limit": 10,
                "fields": "key,title,author_name,first_publish_year,number_of_pages_median"
            }

            response = requests.get(OPENLIB_SEARCH_URL, params=params, timeout=API_TIMEOUT, verify=API_VERIFY_SSL)
            response.raise_for_status()

            docs = response.json().get("docs", [])
            if not docs:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                return None

            # Losowo wybiera książkę z wyników
            book_doc = random.choice(docs)

            # Wyciąga dane książki
            title = book_doc.get("title", "Unknown Title")
            authors = book_doc.get("author_name", ["Unknown Author"])
            if isinstance(authors, list):
                authors = ", ".join(authors[:2])  # Max 2 autorów dla czytelności

            page_count = book_doc.get("number_of_pages_median", 300)
            if not isinstance(page_count, int) or page_count <= 0:
                page_count = 300

            # Wyciąga dane książki z openlibrary_id z klucza, który ma format "/works/OL12345W"
            key = book_doc.get("key", "")
            openlibrary_id = key.split("/")[-1] if key else None

            return {
                "title": title,
                "authors": authors,
                "page_count": page_count,
                "openlibrary_id": openlibrary_id,
                "source": "api"
            }

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Timeout lub problem z połączeniem - retry z exponential backoff
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
                continue
            return None
        except (requests.exceptions.RequestException, ValueError) as e:
            # Inne błędy związane z żądaniem - retry
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
                continue
            return None
        except Exception as e:
            # Nieprzewidziany błąd - retry
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
                continue
            return None

    return None


def get_book_live_or_fallback(genre_name=None, fallback_pool=None, force_api=False):
    """Próbuje pobrać książkę z API, a jeśli to się nie uda, korzysta z puli"""
    # Próbuje pobrać z API
    api_book = fetch_book_from_api(genre_name=genre_name)
    if api_book:
        return api_book

    # Jeśli pula nie jest przekazana, załaduje ją z pliku
    if not fallback_pool:
        from data.data_generator.books import _load_book_pool
        fallback_pool = _load_book_pool()

    # Fallback do puli jeśli API zawiedzie
    if fallback_pool:
        if isinstance(fallback_pool, tuple):
            pool_books, pool_by_genre = fallback_pool
        else:
            pool_books = fallback_pool
            pool_by_genre = {}

        if pool_books:
            # Jeśli jest gatunek i są książki w puli dla tego gatunku, wybiera z nich, w przeciwnym razie z całej puli
            if genre_name and genre_name in pool_by_genre:
                selected = random.choice(pool_by_genre[genre_name])
            else:
                selected = random.choice(pool_books)

            return {
                "title": selected.get("title", "Unknown"),
                "authors": selected.get("authors", "Unknown"),
                "page_count": selected.get("page_count", 300),
                "openlibrary_id": selected.get("openlibrary_id"),
                "source": "pool"
            }