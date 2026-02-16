-- ============================= 
-- TABLE: USERS
-- =============================
-- Reprezentuje użytkowników aplikacji.
-- books_read = łączna liczba książek przeczytanych przez użytkownika.
--              Logika generatora ogranicza tę wartość do realistycznego 
--              poziomu (max 52/rok na każdy rok stażu konta).
-- pages_per_day = średnia dzienna liczba stron czytanych przez aktywnego użytkownika.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id INTEGER UNIQUE,         -- Publiczne ID (np. dla API)
    name TEXT NOT NULL,
    birth_date DATE,                    -- Data urodzenia (YYYY-MM-DD) do wyliczania wieku
    register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Data utworzenia konta
    status TEXT NOT NULL CHECK(status IN ('active','inactive')) DEFAULT 'active',
    last_activity TIMESTAMP,            -- Ostatnia znana aktywność (logowanie lub sesja)
    books_read INTEGER DEFAULT 0,       -- Wartość sumaryczna (nieograniczona w schemacie)
    pages_per_day REAL DEFAULT 0        -- Potencjał czytelniczy (tylko dla active)
);

-- =============================
-- TABLE: GENRES
-- =============================
-- Statystyki agregowane wykorzystywane do dashboardu analitycznego.
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    readers INTEGER DEFAULT 0,          -- Liczba unikalnych czytelników
    avg_rating REAL DEFAULT 0,          -- Symulowana ocena satysfakcji (3.7 - 4.9)
    books_read INTEGER DEFAULT 0,       -- Liczba sesji/aktywności zarejestrowanych dla gatunku
    reading_time_share REAL DEFAULT 0   -- % udział w czasie czytania (dla pasków postępu w UI)
);

-- =============================
-- TABLE: USER_FAVORITE_GENRES
-- =============================
-- Relacja wiele-do-wielu (N:M) definiująca preferencje użytkowników.
CREATE TABLE IF NOT EXISTS user_favorite_genres (
    user_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, genre_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- =============================
-- TABLE: BOOKS
-- =============================
-- Rejestr książek przypisanych do użytkowników lub wygenerowanych dla statystyk.
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    authors TEXT,
    genre_id INTEGER,
    total_pages INTEGER,
    current_page INTEGER DEFAULT 0 CHECK(current_page <= total_pages),
    status TEXT CHECK(status IN ('reading', 'finished')) DEFAULT 'reading',
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finish_date TIMESTAMP,               -- Data zakończenia lektury
    added_by_generator INTEGER DEFAULT 0 CHECK(added_by_generator IN (0,1)),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

-- =============================
-- TABLE: ACTIVITY
-- =============================
-- Historia sesji czytelniczych (podstawa wykresów aktywności dziennej/tygodniowej).
-- pages_read <= 50 zapewnia realizm pojedynczego wpisu w historii.
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Moment rejestracji sesji
    pages_read INTEGER DEFAULT 0 CHECK(pages_read >= 0 AND pages_read <= 250),
    session_minutes INTEGER DEFAULT 0 CHECK(session_minutes >= 0),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- =============================
-- TABLE: CHALLENGES
-- =============================
-- Wyzwania czytelnicze (cele) wyznaczone przez użytkowników.
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    target_books INTEGER NOT NULL,
    progress_books INTEGER DEFAULT 0,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP NOT NULL,
    status TEXT CHECK(status IN ('active', 'finished', 'failed')) DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);