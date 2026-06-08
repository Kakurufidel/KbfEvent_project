from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GuestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.guests'
    label = 'guests'
    verbose_name = _('Guests')
