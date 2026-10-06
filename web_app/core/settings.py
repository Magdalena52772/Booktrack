"""Konfiguracja projektu Django dla aplikacji BookTrack."""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Katalog projektu webowego, względem którego budowane są pozostałe ścieżki.
BASE_DIR = Path(__file__).resolve().parent.parent

# Klucz aplikacji musi pozostać tajny i nie powinien być ujawniany w repozytorium kodu źródłowego.
SECRET_KEY = 'django-insecure-g5^fz+ezq^&%3mm78!r#3l1q(n5dtg#$o8cqf8fmrf-4hmagsr'

# W środowisku produkcyjnym DEBUG powinno być ustawione na False.
DEBUG = True

ALLOWED_HOSTS = []


# Zainstalowane aplikacje Django i aplikacje domenowe BookTrack.

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.main',
    'apps.auth_user',
    'apps.books',
    'apps.user',
    'pages',
]

# Custom user model zgodny z tabelą users z panelu.
AUTH_USER_MODEL = 'pages.BooktrackUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Wspólna baza SQLite panelu administracyjnego.

DEFAULT_BOOKTRACK_DB = BASE_DIR.parent / 'admin_panel' / 'booktrack.db'
BOOKTRACK_DB = Path(
    os.getenv(
        'BOOKTRACK_DB_PATH',
        str(DEFAULT_BOOKTRACK_DB),
    )
)

# Panel PySide6 tworzy bazę i inicjalizuje jej schemat.
# Django tylko łączy się z istniejącym plikiem.
if not BOOKTRACK_DB.is_file():
    raise ImproperlyConfigured(
        f"BookTrack database was not found at {BOOKTRACK_DB}. "
        "Start the admin panel once to create it, or set BOOKTRACK_DB_PATH."
    )

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BOOKTRACK_DB),
    }
}


# Walidatory haseł używane przez formularze Django.

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Ustawienia języka i strefy czasowej.

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Pliki statyczne: arkusze stylów, skrypty i obrazy.

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]
