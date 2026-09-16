"""Turning bytes somebody gave us into an image we are willing to keep.

Two copies come out of here. The *original* is kept exactly as it
arrived, so a better rendition can always be made later. The *display*
copy is re-encoded from scratch, which both shrinks it and drops every
piece of metadata the original carried — EXIF, and with it the GPS
coordinates of where a photo was taken.

Nothing here trusts a filename or a Content-Type header. A file is an
image only if Pillow can decode it.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Final

from PIL import Image, UnidentifiedImageError

from hrcek.core.errors import HrcekError
from hrcek.entries.errors import IMAGE_TOO_LARGE, IMAGE_UNREADABLE, NOT_AN_IMAGE

# Ten megabytes. Family-scale: a phone photo fits several times over.
MAX_BYTES: Final = 10 * 1024 * 1024

# Long edge of the display copy. Big enough to fill a card on a retina
# screen without being a full-resolution download.
DISPLAY_MAX_EDGE: Final = 1280

# Raster formats only. SVG is absent on purpose: it is a document that
# can carry script, not a picture.
ACCEPTED: Final = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "AVIF": "image/avif",
    "GIF": "image/gif",
}

DISPLAY_FORMAT: Final = "avif"
FALLBACK_FORMAT: Final = "webp"
CONTENT_TYPES: Final = {"avif": "image/avif", "webp": "image/webp"}

# Pillow's own ceiling on total pixels, guarding against a small file
# that decodes into gigabytes.
MAX_PIXELS: Final = 50_000_000


@dataclass(frozen=True)
class Prepared:
    """Everything the database needs about one image."""

    original: bytes
    original_content_type: str
    display: bytes
    width: int
    height: int
    checksum: str
    byte_size: int


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(data: bytes, *, _max_pixels: int | None = None) -> Prepared:
    """Validate the bytes and build the display copy.

    `_max_pixels` exists so the decompression-bomb guard can be tested
    without building a bomb.
    """
    if len(data) > MAX_BYTES:
        raise HrcekError(IMAGE_TOO_LARGE, {"limit_bytes": MAX_BYTES})

    source_format = _identify(data)
    display, width, height = _display_copy(data, max_pixels=_max_pixels)
    return Prepared(
        original=data,
        original_content_type=ACCEPTED[source_format],
        display=display,
        width=width,
        height=height,
        checksum=checksum(data),
        byte_size=len(data),
    )


def render(data: bytes, *, fmt: str) -> bytes:
    """Re-encode the original into `fmt` for a browser that needs it."""
    rendition, _width, _height = _display_copy(data, fmt=fmt)
    return rendition


def _identify(data: bytes) -> str:
    """The format Pillow sees, or a refusal."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            found = opened.format
    except UnidentifiedImageError as exc:
        raise HrcekError(NOT_AN_IMAGE) from exc
    except Image.DecompressionBombError as exc:
        raise HrcekError(IMAGE_UNREADABLE) from exc
    except OSError as exc:
        raise HrcekError(IMAGE_UNREADABLE) from exc

    if found not in ACCEPTED:
        raise HrcekError(NOT_AN_IMAGE, {"format": found})
    return found


def _display_copy(
    data: bytes, *, fmt: str = DISPLAY_FORMAT, max_pixels: int | None = None
) -> tuple[bytes, int, int]:
    limit = MAX_PIXELS if max_pixels is None else max_pixels
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = limit
    try:
        with Image.open(io.BytesIO(data)) as opened:
            # An animation is flattened to its first frame: a still is
            # what a card wants, and it keeps the encoder simple.
            opened.load()
            image = opened.convert("RGBA" if _has_alpha(opened) else "RGB")
            image.thumbnail(
                (DISPLAY_MAX_EDGE, DISPLAY_MAX_EDGE), Image.Resampling.LANCZOS
            )
            buffer = io.BytesIO()
            # No exif= argument, so nothing from the original travels.
            image.save(buffer, format=fmt.upper(), quality=62)
            return buffer.getvalue(), image.width, image.height
    except Image.DecompressionBombError as exc:
        raise HrcekError(IMAGE_UNREADABLE, {"limit_pixels": limit}) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HrcekError(IMAGE_UNREADABLE) from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
