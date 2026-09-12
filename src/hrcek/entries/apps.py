from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EntriesConfig(AppConfig):
    name = "hrcek.entries"
    verbose_name = _("Entries")
