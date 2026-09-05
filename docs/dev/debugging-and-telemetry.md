# Debugging and telemetry

## Logs

Every log record is a single line of JSON with `timestamp`, `level`,
`logger`, `message` and `request_id`, plus `exception` when there is a
traceback. One line per record keeps logs greppable and parseable.

```bash
uv run python manage.py runserver | jq 'select(.level == "ERROR")'
```

## Request IDs

Each request gets an id, taken from an `X-Request-ID` header when the
caller supplies a well-formed one and generated otherwise. It is
returned on the response, attached to every log record, and tagged on
the Sentry scope — so a user's report of "it broke" leads to the exact
log lines and the exact Sentry event.

Supplied ids are accepted only if they match `[A-Za-z0-9._-]{1,64}`. The
value is echoed in a response header, so anything that could smuggle
header syntax is replaced rather than sanitised.

## SQL

```bash
HRCEK_DEBUG_SQL=1 uv run python manage.py runserver
```

## Attaching a debugger

```bash
DEBUGPY_ENABLE=1 uv run python manage.py runserver --noreload
```

Then attach your editor's debugger to `127.0.0.1:5678`. Any DAP-capable
client works — the project ships no editor configuration, so use
whatever your editor calls "attach to a running process".

Set `DEBUGPY_WAIT=1` to block startup until the debugger connects, which
is how you catch something that fails during boot. Use `--noreload`, or
the autoreloader will fight for the port.

## Sentry

Sentry is optional and off by default. Set `SENTRY_DSN` to enable it;
leave it empty and the SDK is never initialised, every `sentry_sdk` call
becomes a no-op, and nothing else changes. A test enforces exactly that.

`send_default_pii` is `False`. This project stores what a family reads,
and none of that should leave the machine as a side effect of an error
report.

Unexpected exceptions are reported explicitly from the API's catch-all
handler, because django-ninja handles them before Django's middleware
would see them.
