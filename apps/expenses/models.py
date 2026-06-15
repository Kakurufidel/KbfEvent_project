# apps/expenses/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class BeveragePack(models.Model):
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='beverage_packs',
        verbose_name=_('événement'),
    )
    drink_name = models.CharField(_('nom de la boisson'), max_length=100)
    pack_quantity = models.PositiveIntegerField(_('quantité par pack'))
    pack_price = models.DecimalField(_('prix par pack'), max_digits=12, decimal_places=2)
    unit_type = models.CharField(_('type d\'unité'), max_length=50, blank=True, help_text="ex: bouteille, canette")

    class Meta:
        verbose_name = _('pack de boisson')
        verbose_name_plural = _('packs de boissons')
        unique_together = [('event', 'drink_name')]

    def __str__(self):
        return f"{self.drink_name} - {self.event.name}"