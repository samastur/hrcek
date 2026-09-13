# Hrček

Hrček — a tool for saving interesting online content.

A small, self-hosted service for storing references to things you find
on the web. Built for family-scale use: SQLite, one process, no moving
parts you have to babysit.

## Status

Early. Accounts work — invitations, gated self-signup, email
confirmation, password reset, and API authentication by session or
bearer token. People can manage their own display name, email address,
password and API tokens, and save entries with tags from the web or the
API. Images, custom fields and shared collections are still to come.

## Documentation

- [User manual](docs/manual/index.md)
- [Developer documentation](docs/dev/index.md)
- [API guide](docs/dev/api.md) — for building a client
- [Working agreement](CLAUDE.md)

## Quick start

```bash
uv sync
uv run pytest
uv run python manage.py runserver
```

Requires [uv](https://docs.astral.sh/uv/) and GNU gettext. See
[development setup](docs/dev/development-setup.md).

## Licence

See [LICENSE](LICENSE).
