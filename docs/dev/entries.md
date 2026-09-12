# Entries

The `hrcek.entries` app holds what Hrček is actually for: an `Entry`
belonging to one person, with tags.

## Ownership

Every entry and every tag has an owner, and every query is scoped to
`request.user`. Somebody else's entry answers **404, not 403**; a 403
would confirm the id exists.

Tags belong to a person too. Nina's `watches` and Marko's `watches` are
different rows.

## URL identity

A person cannot hold the same address twice, enforced by a
`UniqueConstraint(owner, url)`. Saving an address already held updates
that entry. This makes a re-run import idempotent, and it is the same
rule on the web form as in the API.

**Matching is deliberately near-exact**: whitespace trimmed, scheme and
host lowercased, nothing else.

Fuller normalisation — trailing slashes, `www.`, stripping `utm_*` — is
a rabbit hole where every rule is wrong for some site, and its failure
mode is silent: two genuinely different pages merge into one entry and
one is lost. Near-exact matching fails visibly instead, as a duplicate
somebody can see and fix. Do not "improve" this without a reason
stronger than tidiness.

## Ordering

`Meta.ordering` is `("-created_at", "-pk")`. The `-pk` is not
decoration: entries saved in one batch share a timestamp to the
microsecond, and without a tiebreaker SQLite is free to order them
differently between queries, so pagination can show a row twice or skip
it. There is a test that fixes two entries to the same instant.

## save_entry is the only writer

`services.save_entry()` is the single place an entry is written. The web
form, the API create endpoint and the batch endpoint all go through it,
so upsert-on-URL, tag assignment and URL validation exist once rather
than in three copies that drift apart.

URL validation lives there rather than on the form for the same reason:
the web form has a `URLField` in front of it, the API has nothing, and
the shared path is where the rule belongs.

## Tags

Parsed from one comma-separated field, trimmed, empties dropped,
deduplicated ignoring case, keeping the first spelling seen. Created on
demand.

`Tag.prune_orphans(owner)` deletes that person's tags that no entry uses
any more, and is called after every save and every delete. Without it
every typo lives in the tag list forever. It is written as
`filter(owner=owner, entries__isnull=True)` — a string lookup rather
than a reverse accessor, because `ty` does not run the django-stubs
plugin and cannot see `tag.entries`.

## The API

```
POST /api/entries/          one entry; 201 created, 200 updated
POST /api/entries/batch/    up to HRCEK_MAX_BATCH; 200 or 207
GET  /api/entries/          your entries, paginated
```

Everything on `EntryIn` except `url` has a default, so a client can post
a bare link. That matters more as later phases add fields: a client that
knows nothing about them must still work.

**The batch contract.** One result per row, in submission order, each
`created`, `updated` or `error`. The call answers **200 when every row
succeeded and 207 when any failed** — a flat 200 would hide the failure
from a client that checks only the status.

**It is not atomic, on purpose.** Each row runs in its own transaction,
so the rows that were fine are saved and re-running fixes only the rows
that were not. A client has to be able to handle a partially applied
import, which is what the per-row results are for.

Exceeding the limit refuses the whole request with `HRC-ENTRY-0001`
rather than saving a prefix — a half-applied batch with no report is
worse than none.
