"""The image pipeline: what we accept, and what we make of it."""

import io

import pytest
from PIL import Image

from hrcek.core.errors import HrcekError
from hrcek.entries import imaging


def _png(width=40, height=30, colour=(200, 80, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg(width=40, height=30) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_a_png_is_accepted_and_described():
    prepared = imaging.prepare(_png())
    assert prepared.original == _png()
    assert prepared.original_content_type == "image/png"
    assert prepared.checksum == imaging.checksum(_png())


def test_the_display_copy_is_avif():
    prepared = imaging.prepare(_png())
    assert prepared.display[:16].find(b"ftyp") != -1, "not an ISO-BMFF container"
    with Image.open(io.BytesIO(prepared.display)) as opened:
        assert opened.format == "AVIF"


def test_a_small_image_is_not_enlarged():
    prepared = imaging.prepare(_png(width=40, height=30))
    assert (prepared.width, prepared.height) == (40, 30)


def test_a_large_image_is_capped_on_its_long_edge():
    prepared = imaging.prepare(_png(width=3000, height=1500))
    assert prepared.width == imaging.DISPLAY_MAX_EDGE
    assert prepared.height == imaging.DISPLAY_MAX_EDGE // 2


def test_exif_does_not_survive_into_the_display_copy():
    buffer = io.BytesIO()
    source = Image.new("RGB", (60, 40), (5, 5, 5))
    exif = source.getexif()
    exif[0x9003] = "2026:01:01 00:00:00"  # DateTimeOriginal
    source.save(buffer, format="JPEG", exif=exif)
    prepared = imaging.prepare(buffer.getvalue())

    with Image.open(io.BytesIO(prepared.display)) as opened:
        assert dict(opened.getexif()) == {}


def test_a_jpeg_is_accepted():
    assert imaging.prepare(_jpeg()).original_content_type == "image/jpeg"


def test_bytes_that_are_not_an_image_are_refused():
    with pytest.raises(HrcekError) as raised:
        imaging.prepare(b"this is not an image, whatever the headers claim")
    assert raised.value.error_code.code == "HRC-IMAGE-0001"


def test_a_pdf_is_refused_even_though_it_is_a_real_file():
    with pytest.raises(HrcekError) as raised:
        imaging.prepare(b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n")
    assert raised.value.error_code.code == "HRC-IMAGE-0001"


def test_an_svg_is_refused():
    # Vector images can carry script; they are not worth the trouble.
    with pytest.raises(HrcekError) as raised:
        imaging.prepare(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    assert raised.value.error_code.code == "HRC-IMAGE-0001"


def test_too_many_bytes_are_refused_before_decoding():
    with pytest.raises(HrcekError) as raised:
        imaging.prepare(b"\x89PNG\r\n\x1a\n" + b"0" * imaging.MAX_BYTES)
    assert raised.value.error_code.code == "HRC-IMAGE-0002"


def test_a_decompression_bomb_is_refused():
    # Pillow raises on absurd pixel counts; we must translate, not crash.
    bomb = io.BytesIO()
    Image.new("L", (1, 1)).save(bomb, format="PNG")
    with pytest.raises(HrcekError) as raised:
        imaging.prepare(bomb.getvalue(), _max_pixels=0)
    assert raised.value.error_code.code == "HRC-IMAGE-0003"


def test_a_rendition_can_be_made_in_webp_for_older_browsers():
    rendition = imaging.render(_png(), fmt="webp")
    with Image.open(io.BytesIO(rendition)) as opened:
        assert opened.format == "WEBP"


def test_the_checksum_is_stable_and_content_addressed():
    assert imaging.checksum(_png()) == imaging.checksum(_png())
    assert imaging.checksum(_png()) != imaging.checksum(_png(colour=(1, 2, 3)))
