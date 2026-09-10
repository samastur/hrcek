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

## Rate limiting

**Hrček does no rate limiting of its own, and this must be provided in
front of it.** Sign-in, signup and password reset are all guessable, and
nothing in the application counts attempts.

That is a deliberate choice, not an oversight: counting attempts means
writing to a single-writer SQLite database on every failed login, which
contends with real traffic to defend against an attack a family-scale
service is unlikely to face. The right place for it costs nothing per
request.

With nginx:

```nginx
limit_req_zone $binary_remote_addr zone=hrcek_login:10m rate=5r/m;

location /api/auth/login { limit_req zone=hrcek_login burst=5 nodelay; }
location /accounts/      { limit_req zone=hrcek_login burst=10 nodelay; }
```

Caddy has `rate_limit`; if you run neither, `fail2ban` watching the
access log does the same job. Whichever you pick, do pick one — without
it an attacker can guess passwords as fast as the network allows.

## Email

Production sends through SMTP, configured with `HRCEK_SMTP_HOST`,
`HRCEK_SMTP_PORT`, `HRCEK_SMTP_USER`, `HRCEK_SMTP_PASSWORD` and
`HRCEK_SMTP_USE_TLS`, and `HRCEK_FROM_EMAIL` as the sender.

`HRCEK_BASE_URL` must be the address people actually reach, because
every link in every email is built from it. Get it wrong and invitations
and password resets point somewhere useless.

## The first account

```bash
uv run python manage.py createsuperuser
```

It asks for an email address and a password and nothing else, and marks
the account confirmed, since nobody could send a confirmation email to
the very first user. Everyone after that arrives by invitation or
through the allowlist.

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
