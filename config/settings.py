"""
Django settings for CaRGen SDLC Programme Management System
"""

import os
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CORE SETTINGS
# =============================================================================
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-cargen-sdlc-local-key")
DEBUG = os.environ.get("DEBUG", True) == True
TESTING = "test" in sys.argv

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
_allowed_hosts_env = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,cargen.5.189.173.50.sslip.io")
ALLOWED_HOSTS = [item.strip() for item in _allowed_hosts_env.split(",") if item.strip()]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip() 
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") 
    if origin.strip()
]

# In development also allow *.localhost and *.lvh.me for subdomain testing
if DEBUG:
    for _dev_host in ['.localhost', '.lvh.me', 'localhost', '127.0.0.1', 'cargen.5.189.173.50.sslip.io/']:
        if _dev_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_dev_host)

# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================
INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Local apps
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
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
def build_database_config():
    """
    Build database configuration from DATABASE_URL or individual DB_* environment variables.
    Supports PostgreSQL, SQLite, and URL-based configuration.
    """
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

    # Use individual DB_* environment variables
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

    # Default to SQLite
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


DATABASES = {
    "default": build_database_config()
}

# =============================================================================
# AUTHENTICATION & AUTHORIZATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = []

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/changes/"
LOGOUT_REDIRECT_URL = "/"

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# =============================================================================
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

# =============================================================================
# MEDIA FILES
# =============================================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logger.debug(
    "Django settings loaded | DEBUG: %s | ALLOWED_HOSTS: %s",
    DEBUG,
    ALLOWED_HOSTS,
)
