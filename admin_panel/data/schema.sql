-- ============================= 
-- TABLE: USERS
-- =============================
-- Reprezentuje użytkowników aplikacji.
-- books_read = łączna liczba książek przeczytanych przez użytkownika
--              w całym czasie trwania konta (wartość agregowana, nie liczona z activity).
-- pages_per_day = średnia dzienna liczba stron czytanych przez aktywnego użytkownika.
--                 Dla inactive użytkowników wartość może być NULL.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    external_id INTEGER UNIQUE, -- publiczne ID
    name TEXT NOT NULL,
    age INTEGER,
    register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL CHECK(status IN ('active','inactive')) DEFAULT 'active',
    last_activity TIMESTAMP,             -- ostatnia znana aktywność użytkownika
    books_read INTEGER DEFAULT 0,
    pages_per_day REAL DEFAULT 0         -- tylko dla active; inactive -> NULL
);

-- =============================
-- TABLE: GENRES
-- =============================
-- Statystyki agregowane na podstawie aktywności użytkowników.
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    readers INTEGER DEFAULT 0,    -- liczba unikalnych czytelników gatunku
    avg_rating REAL DEFAULT 0,       -- symulowana średnia ocena
    books_read INTEGER DEFAULT 0,     -- liczba sesji/aktywności dla gatunku
    reading_time_share REAL DEFAULT 0   -- procentowy udział w całkowitym czytaniu
);

-- =============================
-- TABLE: USER_FAVORITE_GENRES
-- =============================
-- Relacja N:M między użytkownikami a ich ulubionymi gatunkami.
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
-- Książki dodane przez użytkowników lub generator.
-- status = aktualny stan czytania książki.
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
    finish_date TIMESTAMP,
    added_by_generator INTEGER DEFAULT 0 CHECK(added_by_generator IN (0,1)),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

-- =============================
-- TABLE: ACTIVITY
-- =============================
-- Pojedyncze sesje czytelnicze użytkowników.
-- Jedna aktywność ≠ jedna książka ≠ books_read użytkownika.
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pages_read INTEGER DEFAULT 0 CHECK(pages_read >= 0 AND pages_read <= 50),
    session_minutes INTEGER DEFAULT 0 CHECK(session_minutes >= 0),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- =============================
-- TABLE: CHALLENGES
-- =============================
-- Wyzwania czytelnicze użytkowników.
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