# Languages

Hrček speaks English and Slovenian. It does not ask you to choose —
it uses the language your browser or app requests.

## How the language is chosen

Every request carries the languages you prefer, in order. Hrček answers
in the first one it knows, and falls back to English otherwise. Changing
your browser's or phone's preferred language changes Hrček's replies,
with nothing to configure here.

## If a reply is in the wrong language

Check your browser's language settings — the preferred language is set
there, not in Hrček. If Slovenian is listed first and replies still
arrive in English, that is a bug worth reporting.

## Asking for a language directly

If you are calling Hrček from a script:

```bash
curl -H "Accept-Language: sl" http://localhost:8000/api/health
```
