"""Settings for the test suite: fast, deterministic, offline."""

from hrcek.settings.base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-insecure-not-a-real-secret"  # noqa: S105
ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# The suite must never reach Sentry.
SENTRY_DSN = ""
