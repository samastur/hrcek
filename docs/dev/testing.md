# Testing

```bash
uv run pytest                          # everything
uv run pytest tests/core -v            # one directory
uv run pytest tests/test_api.py::test_health_endpoint_reports_ok
uv run pytest --cov=hrcek --cov-report=term-missing
```

## Test-driven development

Write the failing test first. Run it and confirm it fails for the reason
you expect — a test that has never failed has not been shown to test
anything. Then write the smallest code that makes it pass.

## Warnings are errors

The suite runs with `filterwarnings = ["error"]`. A `DeprecationWarning`
fails the run, which is the point: deprecations get fixed while they are
cheap.

**Never silence a warning.** No entries in `filterwarnings`, no
`-W ignore`, no `warnings.simplefilter`. If a warning cannot be fixed —
because it comes from a dependency with no upgrade available — stop and
ask the project owner. That decision is not a developer's to make alone.

## Coverage

Coverage is reported, not gated. A percentage target tends to produce
tests written for the number rather than for the risk.

## What the scaffolding tests guarantee

- Error codes are unique, well-formed, and carry translatable messages.
- Every failure path renders the same JSON shape, and the catch-all
  leaks neither exception text nor traceback.
- Slovenian actually resolves — the gettext pipeline is proven, not just
  configured.
- No model change is missing a migration.
- The application runs, and serves requests, with Sentry unconfigured.
- Every registered error code is documented.
