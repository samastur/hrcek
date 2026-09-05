# Deployment

Hrček is built for family-scale use. One process, one SQLite file, a
reverse proxy in front. No queue, no cache, no container orchestration.

## Steps

```bash
uv sync --locked --no-dev
uv run python manage.py migrate
uv run gunicorn hrcek.wsgi:application --bind 127.0.0.1:8000
```

Compiled translations are committed, so there is no `compilemessages`
step on deploy.

Set `DJANGO_SETTINGS_MODULE=hrcek.settings.prod`, which requires
`HRCEK_SECRET_KEY` and `HRCEK_ALLOWED_HOSTS` and refuses to start
without them. Production also forces `/api/docs` off.

`gunicorn` is not a project dependency; install it alongside, or use
whichever WSGI server you prefer.

## Backups

The database is a single file. Back it up with SQLite's own command,
which is safe while the process is running:

```bash
sqlite3 /path/to/db.sqlite3 ".backup '/path/to/backup.sqlite3'"
```

Copying the file with `cp` while the service is running can capture a
torn write. Use `.backup`.

## Upgrades

```bash
git pull && uv sync --locked --no-dev
uv run python manage.py migrate
# restart the service
```
