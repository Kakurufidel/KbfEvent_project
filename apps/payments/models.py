from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.events.models import Event


class PaymentRequest(models.Model):
    class Plan(models.TextChoices):
        BASIC = 'basic', _('Basic (25 USD)')
        PREMIUM = 'premium', _('Premium (40 USD)')

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        APPROVED = 'approved', _('Approuvé')
        REJECTED = 'rejected', _('Rejeté')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_requests',
        verbose_name=_('utilisateur'),
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='payment_requests',
        verbose_name=_('événement'),
    )
    plan = models.CharField(_('plan'), max_length=10, choices=Plan.choices)
    amount = models.DecimalField(_('montant'), max_digits=10, decimal_places=2, editable=False)
    screenshot = models.ImageField(_('capture d\'écran'), upload_to='payment_screenshots/%Y/%m/%d/')
    status = models.CharField(_('statut'), max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_notes = models.TextField(_('notes admin'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(_('approuvé le'), null=True, blank=True)

    class Meta:
        verbose_name = _('demande de paiement')
        verbose_name_plural = _('demandes de paiement')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk and not self.amount:
            if self.plan == self.Plan.BASIC:
                self.amount = 25.00
            else:
                self.amount = 40.00
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.event.name} ({self.get_plan_display()})"