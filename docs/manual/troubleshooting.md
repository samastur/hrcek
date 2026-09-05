# When something goes wrong

Hrček reports every problem with a code such as `HRC-CORE-0003`, along
with a description in your language. The description may be reworded
between versions; **the code never changes meaning**, so quote the code
when asking for help.

A failure looks like this:

```json
{
  "error": {
    "code": "HRC-CORE-0003",
    "message": "The requested resource does not exist.",
    "details": {}
  }
}
```

## What the codes mean

| Code | What happened | What to do |
|---|---|---|
| `HRC-CORE-0001` | Something went wrong inside Hrček. | Not your fault. Report it, with the code, the time, and what you were doing. |
| `HRC-CORE-0002` | The information sent was not valid. | Check what you entered. `details` names the fields at fault. |
| `HRC-CORE-0003` | The thing you asked for does not exist. | Check the address or the identifier. It may also have been deleted. |

## Reporting a problem

Include the error code, roughly when it happened, and what you were
doing. If you can see the response headers, include `X-Request-ID` — it
points straight at the matching entry in the logs.
