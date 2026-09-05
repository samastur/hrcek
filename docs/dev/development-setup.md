# Development setup

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — manages Python and dependencies
- GNU gettext — `makemessages` and `compilemessages` shell out to it
  - macOS: `brew install gettext`
  - Debian/Ubuntu: `sudo apt-get install gettext`
- [prek](https://github.com/j178/prek) — runs the git hooks

## First run

```bash
uv sync
uv tool install prek
prek install
uv run pytest
uv run python manage.py runserver
```

The API is then at `http://127.0.0.1:8000/api/`, with interactive
documentation at `/api/docs` and a health check at `/api/health`.

## Configuration

Settings read the environment, optionally seeded from a `.env` file at
the repository root. Real environment variables always win, so a stray
file cannot surprise a deployment.

| Variable | Default | Meaning |
|---|---|---|
| `HRCEK_SECRET_KEY` | — | Required in production; dev and test use a fixed non-secret |
| `HRCEK_DEBUG` | `false` | Django debug mode |
| `HRCEK_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `HRCEK_DB_PATH` | `db.sqlite3` | SQLite file location |
| `HRCEK_DEBUG_SQL` | `false` | Log every query |
| `HRCEK_API_DOCS` | `true` | Serve `/api/docs`; forced off in production |
| `SENTRY_DSN` | empty | Empty disables Sentry entirely |
| `SENTRY_ENVIRONMENT` | `development` | Tags reported events |
| `SENTRY_TRACES_SAMPLE_RATE` | `1.0` | Trace sampling |
| `DEBUGPY_ENABLE` | `false` | Start a debugpy listener |
| `DEBUGPY_PORT` | `5678` | Port for that listener |
| `DEBUGPY_WAIT` | `false` | Block until a debugger attaches |

`.env` is gitignored. Never commit real secrets.

## Editor

No editor configuration is committed. Debugging works from any editor:
`DEBUGPY_ENABLE=1` opens a plain debugpy port to attach to. See
[debugging and telemetry](debugging-and-telemetry.md).
