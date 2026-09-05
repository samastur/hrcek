"""Production settings. Every secret comes from the environment."""

from hrcek.settings.base import *  # noqa: F403
from hrcek.settings.env import env_list, env_str

DEBUG = False
API_DOCS_ENABLED = False
SECRET_KEY = env_str("HRCEK_SECRET_KEY")
ALLOWED_HOSTS = env_list("HRCEK_ALLOWED_HOSTS")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
