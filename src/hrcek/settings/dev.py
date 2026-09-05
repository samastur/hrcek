"""Local development settings."""

from hrcek.settings.base import *  # noqa: F403
from hrcek.settings.env import env_bool, env_int

DEBUG = True
SECRET_KEY = "dev-insecure-not-a-real-secret"  # noqa: S105
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Attach a debugger with DEBUGPY_ENABLE=1; see
# docs/dev/debugging-and-telemetry.md
DEBUGPY_ENABLE = env_bool("DEBUGPY_ENABLE", default=False)
DEBUGPY_PORT = env_int("DEBUGPY_PORT", default=5678)
DEBUGPY_WAIT = env_bool("DEBUGPY_WAIT", default=False)
