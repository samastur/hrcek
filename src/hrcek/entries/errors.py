"""Error codes owned by the entries app."""

from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

BATCH_TOO_LARGE = register("HRC-ENTRY-0001", 422, _("Too many entries in one request."))
