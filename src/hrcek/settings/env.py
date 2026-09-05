"""Typed access to environment variables, with an optional .env file.

A dedicated helper keeps settings modules readable and turns a missing
or malformed variable into one clear error instead of a KeyError or a
silently wrong value.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})

_MISSING = object()


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from *path* without overriding real env vars.

    Real environment variables always win, so a deployment cannot be
    surprised by a stray file. Absent files are ignored.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def _raw(name: str, default: object) -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    if default is _MISSING:
        raise ImproperlyConfigured(f"Required environment variable {name} is not set.")
    return str(default)


def env_str(name: str, default: str | None = None) -> str:
    return _raw(name, _MISSING if default is None else default)


def env_bool(name: str, default: bool | None = None) -> bool:
    if default is None and name not in os.environ:
        raise ImproperlyConfigured(f"Required environment variable {name} is not set.")
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ImproperlyConfigured(
        f"Environment variable {name} must be a boolean, got {raw!r}."
    )


def env_int(name: str, default: int | None = None) -> int:
    raw = _raw(name, _MISSING if default is None else default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be an integer, got {raw!r}."
        ) from exc


def env_float(name: str, default: float | None = None) -> float:
    raw = _raw(name, _MISSING if default is None else default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be a number, got {raw!r}."
        ) from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    if name not in os.environ:
        if default is None:
            raise ImproperlyConfigured(
                f"Required environment variable {name} is not set."
            )
        return list(default)
    return [part.strip() for part in os.environ[name].split(",") if part.strip()]
