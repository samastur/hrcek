"""Error codes owned by the entries app."""

from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

BATCH_TOO_LARGE = register("HRC-ENTRY-0001", 422, _("Too many entries in one request."))

UNKNOWN_FIELD = register("HRC-FIELD-0001", 422, _("There is no field with that name."))
