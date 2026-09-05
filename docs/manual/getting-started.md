# Getting started

Hrček runs as a small web service on a machine you control — a home
server, a spare computer, a small VPS. Whoever set it up can tell you its
address; the examples below assume `http://localhost:8000`.

## Checking that it is running

Open `http://localhost:8000/api/health` in a browser. A healthy service
answers:

```json
{
  "status": "ok",
  "service": "hrcek",
  "version": "0.1.0",
  "message": "Service is running."
}
```

If the page does not load at all, Hrček is not running. Ask whoever
looks after it to start the service.

## Browsing what Hrček can do

`http://localhost:8000/api/docs` lists every available operation and
lets you try each one from the browser. It is the quickest way to see
what the current version supports.

This page is switched off on production installations, so it may not be
available on yours.
