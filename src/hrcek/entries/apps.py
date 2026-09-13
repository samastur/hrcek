from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EntriesConfig(AppConfig):
    name = "hrcek.entries"
    verbose_name = _("Entries")

    def ready(self) -> None:
        # Deferred on purpose: the app registry is not ready at import
        # time, and the signal module reaches for models.
        from hrcek.entries import signals  # noqa: F401, PLC0415
