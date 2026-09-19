"""Error codes owned by the collections app."""

from django.utils.translation import gettext_lazy as _

from hrcek.core.errors import register

NOT_YOURS = register("HRC-COLL-0001", 404, _("That entry is not yours to collect."))
NOT_A_MANUAL_COLLECTION = register(
    "HRC-COLL-0002",
    422,
    _("This collection follows a label, so entries cannot be added by hand."),
)
