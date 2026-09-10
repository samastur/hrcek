"""Settings shared by every environment."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Any

from django.utils.translation import gettext_lazy as _

from hrcek.core.telemetry import configure_sentry
from hrcek.settings.env import (
    env_bool,
    env_float,
    env_int,
    env_list,
    env_str,
    load_dotenv,
)

BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(BASE_DIR / ".env")

HRCEK_VERSION = version("hrcek")

# Every environment module either overrides this (dev, test) or requires
# it from the environment (prod). It must NOT be required here: base.py
# runs to completion before the module importing it can override
# anything, so a required read would make dev and test unimportable.
SECRET_KEY = env_str("HRCEK_SECRET_KEY", "")
DEBUG = env_bool("HRCEK_DEBUG", default=False)
ALLOWED_HOSTS = env_list("HRCEK_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    # Not "django.contrib.admin": this subclass swaps in Hrcek's own
    # admin site while keeping autodiscovery.
    "hrcek.accounts.admin_site.HrcekAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ninja",
    "hrcek.core",
    "hrcek.accounts",
]

MIDDLEWARE = [
    "hrcek.core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Session must precede authentication and locale; CSRF must precede
    # authentication.
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

API_DOCS_ENABLED = env_bool("HRCEK_API_DOCS", default=True)

ROOT_URLCONF = "hrcek.urls"
WSGI_APPLICATION = "hrcek.wsgi.application"
ASGI_APPLICATION = "hrcek.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env_str("HRCEK_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            # WAL lets readers proceed while a write is in flight, and
            # IMMEDIATE takes the write lock up front instead of failing
            # partway through. The right shape for one small writer.
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "hrcek.accounts.backends.EmailOrDisplayNameBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", _("English")),
    ("sl", _("Slovenian")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

HRCEK_BASE_URL = env_str("HRCEK_BASE_URL", "http://localhost:8000")
HRCEK_INVITATION_EXPIRY_DAYS = env_int("HRCEK_INVITATION_EXPIRY_DAYS", 7)
DEFAULT_FROM_EMAIL = env_str("HRCEK_FROM_EMAIL", "hrcek@localhost")

# Django 6.1's mailers API. The old EMAIL_* settings, and the
# fail_silently and connection arguments, all raise
# RemovedInDjango70Warning, which this project's test suite treats as an
# error. Leaving MAILERS undefined warns too.
MAILERS: dict[str, dict[str, Any]] = {
    "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
}

STATIC_URL = "static/"

DEBUG_SQL = env_bool("HRCEK_DEBUG_SQL", default=False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "hrcek.core.logging.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG_SQL else "INFO",
            "propagate": False,
        },
    },
}

SENTRY_DSN = env_str("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = env_str("SENTRY_ENVIRONMENT", "development")
# Family-scale traffic: sampling would discard signal and save nothing.
SENTRY_TRACES_SAMPLE_RATE = env_float("SENTRY_TRACES_SAMPLE_RATE", 1.0)

configure_sentry(
    SENTRY_DSN,
    environment=SENTRY_ENVIRONMENT,
    release=f"hrcek@{HRCEK_VERSION}",
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
)
