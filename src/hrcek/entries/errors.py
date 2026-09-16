"""Error codes owned by the entries app."""

from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

BATCH_TOO_LARGE = register("HRC-ENTRY-0001", 422, _("Too many entries in one request."))

UNKNOWN_FIELD = register("HRC-FIELD-0001", 422, _("There is no field with that name."))

NOT_AN_IMAGE = register(
    "HRC-IMAGE-0001", 422, _("That file is not an image Hrček can read.")
)
IMAGE_TOO_LARGE = register("HRC-IMAGE-0002", 422, _("That image is too large."))
IMAGE_UNREADABLE = register(
    "HRC-IMAGE-0003", 422, _("That image could not be read; it may be damaged.")
)
