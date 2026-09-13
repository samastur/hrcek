# The API

Hrček has a small HTTP API for saving entries from scripts and other
programs. This page is written for somebody building a client.

## What it is for, and what it is not

The API **saves and reads entries**. It deliberately cannot create
accounts, change a password, or manage API tokens: those are web-only,
because each involves a confirmation or a re-authentication step that
does not belong in a script. If your client needs one of them, send the
person to the website.

## Base address and stability

Everything lives under `/api/` on whatever address your Hrček is served
from. There is no version in the path. The API is at `1.0.0`, reported
in the OpenAPI schema.

What is stable: paths, the error envelope, and **error codes**. What is
not: the human-readable text of messages, which is translated and may be
reworded. Branch on `code`, never on `message`.

## Authentication

Every endpoint requires credentials except `GET /api/health` and
`POST /api/auth/login`.

**Use a bearer token.** Create one on your account page at
`/accounts/me/`; it is shown once, so copy it then. Tokens look like
`hrcek_` followed by random characters.

```bash
curl -H "Authorization: Bearer hrcek_8Xr2mQ7pLk4vNs1TzYbW..." \
     https://hrcek.example.com/api/auth/me
```

Session cookies also work, which is how the website itself talks to the
API. **Scripts should use tokens**: a session makes unsafe requests
subject to CSRF checks, and a token does not. A token is refused if it
is unknown, revoked, expired, or belongs to a disabled account.

Without credentials:

```json
{"error": {"code": "HRC-AUTH-0003",
           "message": "You must sign in to do that.", "details": {}}}
```

## Errors

Every failure has the same shape and a truthful status code:

```json
{"error": {"code": "HRC-CORE-0002",
           "message": "The submitted data is not valid.",
           "details": {"url": ["Enter a valid URL."]}}}
```

`code` identifies the condition and never changes meaning. `message` is
for showing a person and is translated. `details` carries whatever
machine-readable context the condition has, and may be empty.

Statuses mean what they usually mean: 401 you are not authenticated, 403
you are not allowed, 404 it is not there, 409 a conflict, 422 the input
is wrong, 500 our fault. A failure is never returned as 2xx.

Every code is listed in [error codes](error-codes.md).

## Saving an entry

`POST /api/entries/` — the main thing the API is for.

```bash
curl -X POST https://hrcek.example.com/api/entries/ \
  -H "Authorization: Bearer $HRCEK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/watch",
       "title": "A watch",
       "notes": "38mm, sapphire",
       "tags": ["watches", "diving"]}'
```

Only `url` is required. `title`, `notes` and `tags` all default to
empty, so a minimal client can post a bare link and nothing else. Later
versions will add fields; they will all have defaults too, so a client
that does not know about them keeps working.

**201** when the entry was created:

```json
{"id": 1,
 "url": "https://example.com/watch",
 "title": "A watch",
 "notes": "38mm, sapphire",
 "tags": ["diving", "watches"],
 "created_at": "2026-09-13T11:01:21.385Z",
 "updated_at": "2026-09-13T11:01:21.385Z"}
```

**200** when an entry for that address already existed and was updated.
The status is how you tell which happened without comparing ids.

### Saving an address you already hold replaces the entry

You cannot hold the same address twice. Posting one you already have
updates that entry — which is what makes re-running an import safe.

**It is a replace, not a patch.** Fields you leave out take their
defaults, so they are cleared. Posting this:

```json
{"url": "https://example.com/watch", "title": "A watch, revisited"}
```

over the entry above leaves `notes` empty and `tags` empty:

```json
{"id": 1, "url": "https://example.com/watch",
 "title": "A watch, revisited", "notes": "", "tags": [],
 "created_at": "2026-09-13T11:01:21.385Z",
 "updated_at": "2026-09-13T11:01:21.388Z"}
```

If your client means to change one field, read the entry first and send
the whole thing back. There is no PATCH.

Addresses are matched almost exactly: surrounding whitespace is
ignored and the scheme and host are lowercased, and nothing else. A
trailing slash, a `www.`, or a tracking parameter makes it a different
address.

## Saving many entries at once

`POST /api/entries/batch/` takes an array of the same objects, up to 200
per call, and answers with one result per row **in the order you sent
them**.

```bash
curl -X POST https://hrcek.example.com/api/entries/batch/ \
  -H "Authorization: Bearer $HRCEK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"url": "https://example.com/a"}, {"url": "not a url"}]'
```

```json
{"results": [
  {"index": 0, "status": "created", "id": 2, "error": null},
  {"index": 1, "status": "error", "id": null,
   "error": {"code": "HRC-CORE-0002",
             "message": "The submitted data is not valid.",
             "details": {"url": ["Enter a valid URL."]}}}
]}
```

`status` is `created`, `updated` or `error`. `id` is set for the first
two; `error` for the third.

**The status code tells you whether anything failed**: **200** if every
row succeeded, **207** if any did not. Check the status first, then walk
the results.

**The call is not atomic, on purpose.** Rows that validate are saved
even when siblings fail. A 300-row import does not die on row 200, and
re-running it fixes the rows that were wrong while the ones that were
right are simply updated in place. Your client has to be able to handle
a partially applied batch; the per-row results are what makes that
possible.

Sending more than 200 rows refuses the **whole** request with
`HRC-ENTRY-0001` and saves nothing — a half-applied batch with no report
would be worse than none.

## Reading entries

`GET /api/entries/` returns your own entries, newest first, paginated.

```json
{"items": [{"id": 1, "url": "https://example.com/watch",
            "title": "A watch, revisited", "notes": "", "tags": [],
            "created_at": "2026-09-13T11:01:21.385Z",
            "updated_at": "2026-09-13T11:01:21.388Z"}],
 "count": 1}
```

`count` is the total across all pages. Use `?limit=` and `?offset=` to
page through it.

You only ever see your own entries. Two people may hold the same
address; their entries are unrelated.

## The other endpoints

`GET /api/health` needs no credentials and reports that the service is
up. Useful for monitoring.

```json
{"status": "ok", "service": "hrcek", "version": "0.1.0",
 "message": "Service is running."}
```

`POST /api/auth/login` takes `{"identifier": "...", "password": "..."}`
and starts a **session**. `identifier` is an email address or a display
name. It answers 401 with `HRC-AUTH-0001` for bad credentials and 403
with `HRC-AUTH-0002` if the address has never been confirmed. Scripts
do not need this; use a token.

`POST /api/auth/logout` ends that session and answers 204.

`GET /api/auth/me` reports who you are:

```json
{"email": "nina@example.com", "display_name": null}
```

It is the cheapest way for a client to check that its token works.

## Languages

Error messages are translated. Send `Accept-Language: sl` and you get
Slovenian; anything unrecognised falls back to English. Codes never
change, which is why clients should branch on them.

## Machine-readable schema

The OpenAPI schema is committed at [`../api/openapi.json`](../api/openapi.json),
so you can generate a client without running Hrček:

```bash
openapi-generator-cli generate -i docs/api/openapi.json -g python
```

A hook keeps it in step with the code; it cannot drift from what the
server actually serves.

A running instance also serves interactive documentation at `/api/docs`,
where each endpoint can be tried in the browser. **Production disables
it** (`HRCEK_API_DOCS=false`), so on a deployed Hrček use the committed
schema.
