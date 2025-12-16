-- =============================
-- TABLE: USERS
-- =============================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('active','inactive')) DEFAULT 'active',
    last_activity TIMESTAMP,
    books_read INTEGER DEFAULT 0,
    pages_per_day REAL DEFAULT 0
);


-- =============================
-- TABLE: GENRES
-- =============================
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    readers INTEGER DEFAULT 0,
    avg_rating REAL DEFAULT 0,
    books_read INTEGER DEFAULT 0,
    reading_time_share REAL DEFAULT 0
);

-- =============================
-- TABLE: USER_FAVORITE_GENRES
-- =============================
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
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    authors TEXT,
    genre_id INTEGER,
    total_pages INTEGER,
    current_page INTEGER DEFAULT 0,
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
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pages_read INTEGER DEFAULT 0,
    session_minutes INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- =============================
-- TABLE: CHALLENGES
-- =============================
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
