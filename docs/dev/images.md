# Images

An entry may carry one picture. This page covers how it is stored and
rendered; the sections on fetching, serving and the API arrive with
those layers.

## Two copies, two jobs

`EntryImage` (`src/hrcek/entries/models.py`) is a separate table with a
one-to-one link to `Entry`, not a set of columns on `Entry` itself.
SQLite stores a row's blobs inline, so keeping them on `Entry` would
mean every entry list read megabytes it did not want. Nothing joins
this table unless a page actually shows a picture.

Each image is kept twice:

| Column | What it is | Who sees it |
|---|---|---|
| `original` | The bytes exactly as they arrived | Nobody. Archival only. |
| `display` | Re-encoded AVIF, long edge ≤ 1280 px | Browsers |

The original is kept so a better rendition can always be made later —
a different format, a different size — without asking anyone to upload
anything again. It is never served, which also means the EXIF it
carries, including the GPS coordinates of where a photo was taken,
never reaches a reader. The display copy is built by decoding and
re-saving, so no metadata survives into it.

## What counts as an image

`src/hrcek/entries/imaging.py` decides. A filename proves nothing and
a `Content-Type` header proves less: bytes are an image only if Pillow
can decode them. Accepted formats are PNG, JPEG, WebP, AVIF and GIF.

SVG is refused deliberately. It is a document that can carry script,
not a picture, and serving one from our own origin would hand somebody
else's markup our cookies.

Two limits guard the decoder: `MAX_BYTES` (10 MB) is checked before
anything is parsed, and `MAX_PIXELS` (50 million) caps what a small
file is allowed to decode into, so a decompression bomb fails loudly
instead of eating the machine. Both refusals carry registered error
codes — see [error codes](error-codes.md).

## The filesystem cache

`MEDIA_ROOT` (set with `HRCEK_MEDIA_PATH`, default `media/` beside the
database) holds rendered copies at
`images/<first two characters of the checksum>/<checksum>.<format>`.
The path is content-addressed, so the same bytes always land in the
same file and a replaced image never collides with its predecessor.

**The cache is disposable.** Delete the whole directory and the next
request writes it again from the database. It exists so serving a page
does not mean pulling a blob through the ORM, not as a second source of
truth. Files are written beside the target and moved into place, so a
reader never sees a half-written file.

`EntryImage.rendition(fmt)` is the only way to read image bytes: it
returns the cached file when there is one and rebuilds it when there is
not. Asking for a format other than AVIF re-encodes from the original,
which is how an older browser gets WebP.
