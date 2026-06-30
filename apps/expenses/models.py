from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class BeveragePack(models.Model):
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='beverage_packs',
        verbose_name=_('événement')
    )
    drink_name = models.CharField(_('nom de la boisson'), max_length=100)
    pack_quantity = models.PositiveIntegerField(_('quantité par pack'), default=12)
    pack_price = models.DecimalField(_('prix par pack'), max_digits=12, decimal_places=2, default=0)
    unit_type = models.CharField(_('type d\'unité'), max_length=50, blank=True, help_text="ex: bouteille, canette")
    is_active = models.BooleanField(_('actif'), default=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('pack de boisson')
        verbose_name_plural = _('packs de boissons')
        unique_together = [('event', 'drink_name')]
        ordering = ['drink_name']

    def __str__(self):
        return f"{self.drink_name} - {self.event.name}"

    def unit_price(self):
        """Prix unitaire de la boisson"""
        if self.pack_quantity > 0:
            return self.pack_price / self.pack_quantity
        return Decimal('0')