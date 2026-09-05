# Error codes

Every failure a client can see has a code. Codes are stable: the text
of a message may be reworded or translated, but a code never changes
meaning and is never reused.

## Format

`HRC-<DOMAIN>-<NNNN>`

`DOMAIN` is three to six uppercase letters naming the area (`CORE`,
later `ITEM`). `NNNN` is a four-digit number unique within that domain.
`HRC-TEST-9xxx` is reserved for the test suite and must never be used by
real code.

## Adding a code

Register it in the owning app's `errors.py`:

```python
from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

ITEM_NOT_FOUND = register("HRC-ITEM-0001", 404, _("The saved item does not exist."))
```

Then add a row to the table below. A test fails if a registered code is
missing here, or if this file lists a code that no longer exists.

Raise it with `HrcekError`:

```python
raise HrcekError(ITEM_NOT_FOUND, {"item_id": item_id})
```

`details` carries machine-readable context. It is never translated and
must never contain anything private.

## Registered codes

| Code | Status | Meaning |
|---|---|---|
| `HRC-CORE-0001` | 500 | An unexpected error occurred. The traceback is in the logs and in Sentry; the client is told nothing more. |
| `HRC-CORE-0002` | 422 | The submitted data is not valid. `details.fields` lists the offending fields. |
| `HRC-CORE-0003` | 404 | The requested resource does not exist. |

## Response shape

```json
{
  "error": {
    "code": "HRC-CORE-0003",
    "message": "The requested resource does not exist.",
    "details": {}
  }
}
```

`message` is translated into the language negotiated from
`Accept-Language`. Clients that need to branch on a failure must switch
on `code`, never on `message`.
