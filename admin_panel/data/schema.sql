-- ============================= 
-- TABLE: USERS
-- =============================
-- Reprezentuje użytkowników aplikacji.
-- pages_per_day = średnia dzienna liczba stron czytanych przez aktywnego użytkownika.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password TEXT NOT NULL,              -- Zahashowane hasło Django
    last_login TIMESTAMP,
    is_superuser INTEGER NOT NULL DEFAULT 0,
    username TEXT NOT NULL UNIQUE,       -- Nickname użytkownika
    email TEXT,
    name TEXT,                           -- Pełne imię i nazwisko
    is_staff INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    date_joined TIMESTAMP NOT NULL,      -- Data dołączenia
    external_id INTEGER UNIQUE,          -- Publiczne ID (np. dla API)
    birth_date DATE NOT NULL CHECK(birth_date < CURRENT_DATE),     -- Data urodzenia (YYYY-MM-DD) do wyliczania wieku
    status TEXT NOT NULL CHECK(status IN ('active','inactive')) DEFAULT 'active',
    last_activity TIMESTAMP,             -- Ostatnia znana aktywność (logowanie lub sesja)
    r_tier TEXT DEFAULT 'regular',
    cluster_group INTEGER DEFAULT NULL,  -- Kolumna pod algorytm klasteryzacji
    books_read INTEGER DEFAULT 0,        -- Wartość sumaryczna
    pages_per_day REAL DEFAULT 0,        -- Potencjał czytelniczy
    current_streak INTEGER DEFAULT 0
);

-- =============================
-- TABLE: GENRES
-- =============================
-- Statystyki agregowane wykorzystywane do dashboardu analitycznego.
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    readers INTEGER DEFAULT 0,           -- Liczba unikalnych czytelników
    avg_rating REAL DEFAULT 0,           -- ocena satysfakcji
    books_read INTEGER DEFAULT 0,        -- Liczba sesji/aktywności zarejestrowanych dla gatunku
    reading_time_share REAL DEFAULT 0    -- % udział w czasie czytania (dla pasków postępu w UI)
);

-- =============================
-- TABLE: USER_FAVORITE_GENRES
-- =============================
-- Relacja wiele-do-wielu (N:M) definiująca preferencje użytkowników.
CREATE TABLE IF NOT EXISTS user_favorite_genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE,
    UNIQUE(user_id, genre_id)
);

-- =============================
-- TABLE: BOOKS
-- =============================
-- Rejestr książek przypisanych do użytkowników lub wygenerowanych dla statystyk.
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    authors TEXT,
    openlibrary_id TEXT,
    genre_id INTEGER,
    total_pages INTEGER,
    current_page INTEGER DEFAULT 0 CHECK(current_page <= total_pages),
    status TEXT CHECK(status IN ('reading', 'finished')) DEFAULT 'reading',
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finish_date TIMESTAMP,                -- Data zakończenia lektury
    added_by_generator INTEGER DEFAULT 0 CHECK(added_by_generator IN (0,1)),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

-- =============================
-- TABLE: ACTIVITY
-- =============================
-- Historia sesji czytelniczych (podstawa wykresów aktywności dziennej/tygodniowej)
-- pages_read <= 50 zapewnia realizm pojedynczego wpisu w historii
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
-- Wyzwania czytelnicze (cele) wyznaczone przez użytkowników
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('quantity', 'genre', 'streak')) NOT NULL,
    target_value INTEGER NOT NULL,      -- liczba książek / liczba dni streaka
    current_value INTEGER DEFAULT 0,    -- Aktualny postęp
    genre_id INTEGER DEFAULT NULL,      -- Tylko dla wyzwań typu 'genre'
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE NOT NULL,
    status TEXT CHECK(status IN ('active', 'finished', 'failed')) DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);


-- =============================
-- TABLE: ACHIEVEMENTS
-- =============================
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_type TEXT NOT NULL, -- np. 'Collector', 'Sprint', 'Marathon'
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_viewed INTEGER DEFAULT 0,    -- Obsługa "czerwonej kropki"
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, achievement_type) -- Zapobiega dublowaniu tej samej odznaki
);

-- Optymalizacja zapytań agregujących
-- Indeks na książki: przyspiesza COUNT(DISTINCT b.id) przy filtrowaniu po statusie
CREATE INDEX IF NOT EXISTS idx_books_user_status ON books(user_id, status);

-- Indeks na aktywność: kluczowy dla SUM(a.pages_read) i filtrowania po dacie
CREATE INDEX IF NOT EXISTS idx_activity_user_timestamp ON activity(user_id, timestamp);

-- Indeks na użytkowników: przyspiesza wyszukiwanie po nicku i mailu
CREATE INDEX IF NOT EXISTS idx_users_search ON users(username, email, name);

-- Tabela meta do przechowywania kluczowych wartości, np. ostatnia aktywność, globalne statystyki itp.
CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT
);

-- Indeks na timestamp w activity dla szybszych zapytań czasowych (np. aktywność dzienna/tygodniowa)
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity(timestamp);