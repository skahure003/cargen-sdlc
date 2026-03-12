import os
from pathlib import Path
import sys
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name: str, default: str = ""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def build_database_config():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme in {"postgres", "postgresql"}:
            return {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed.path.lstrip("/"),
                "USER": parsed.username or "",
                "PASSWORD": parsed.password or "",
                "HOST": parsed.hostname or "",
                "PORT": str(parsed.port or "5432"),
                "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
                "OPTIONS": {
                    "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
                },
            }
        if parsed.scheme == "sqlite":
            sqlite_path = parsed.path.lstrip("/") or "db.sqlite3"
            return {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / sqlite_path,
            }

    if os.environ.get("DB_HOST"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "cargen_sdlc"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            "OPTIONS": {
                "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
            },
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-cargen-sdlc-local-key")
DEBUG = os.environ.get("DEBUG", "1") == "1"
TESTING = "test" in sys.argv
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "change_management",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": build_database_config()
}

AUTH_PASSWORD_VALIDATORS = []
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/changes/"
LOGOUT_REDIRECT_URL = "/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
