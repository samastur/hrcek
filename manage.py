#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path

from hrcek.core.debugging import maybe_start_debugger
from hrcek.settings.env import env_bool, env_int, load_dotenv


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrcek.settings.dev")
    load_dotenv(Path(__file__).resolve().parent / ".env")

    # RUN_MAIN is set in runserver's reloader child; without this guard
    # both processes would race for the debug port.
    if os.environ.get("RUN_MAIN") != "true":
        maybe_start_debugger(
            enabled=env_bool("DEBUGPY_ENABLE", default=False),
            port=env_int("DEBUGPY_PORT", default=5678),
            wait=env_bool("DEBUGPY_WAIT", default=False),
        )

    # Imported here, not at module level: the debugger must be able to
    # attach before Django starts loading settings and apps.
    from django.core.management import (  # noqa: PLC0415
        execute_from_command_line,
    )

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
