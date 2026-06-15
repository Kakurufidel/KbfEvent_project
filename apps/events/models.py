import uuid
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from urllib.parse import quote
from datetime import datetime, timedelta


class Event(models.Model):
    """
    Modèle principal d'événement avec tokens pour RSVP et co-organisateurs
    """
    
    class EventType(models.TextChoices):
        WEDDING = 'wedding', _('Mariage')
        BIRTHDAY = 'birthday', _('Anniversaire')
        CORPORATE = 'corporate', _('Corporate')
        GRADUATION = 'graduation', _('Remise de diplôme')
        OTHER = 'other', _('Autre')
    
    # ========== ORGANISATEUR PRINCIPAL ==========
    main_organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_events',
        verbose_name=_('organisateur principal'),
    )
    
    # ========== INFORMATIONS ÉVÉNEMENT ==========
    name = models.CharField(_('nom'), max_length=200)
    event_type = models.CharField(
        _('type d\'événement'),
        max_length=20,
        choices=EventType.choices,
    )
    event_type_other = models.CharField(
        _('autre type'),
        max_length=100,
        blank=True,
    )
    description = models.TextField(_('description'), blank=True)
    
    # ========== DATE ET LIEU ==========
    date = models.DateField(_('date'), null=True, blank=True)
    time = models.TimeField(_('heure'), null=True, blank=True)
    location = models.CharField(_('lieu'), max_length=500)
    google_maps_link = models.URLField(_('lien Google Maps'), blank=True)
    
    # ========== OPTIONS ÉVÉNEMENT ==========
    dress_code = models.CharField(_('code vestimentaire'), max_length=200, blank=True)
    drink_options = models.JSONField(_('options de boissons'), default=list)
    reminder_message = models.TextField(_('message de rappel'), blank=True)
    sender_email = models.EmailField(_('email expéditeur'), default='noreply@kbfeven.com')
    
    # ========== TOKENS ET SLUG ==========
    rsvp_token = models.CharField(_('token RSVP'), max_length=36, unique=True, blank=True)
    coorganizer_token = models.CharField(_('token co-organisateur'), max_length=36, unique=True, blank=True)
    slug = models.SlugField(_('slug'), unique=True, max_length=200, blank=True)
    
    # ========== STATUT ==========
    is_active = models.BooleanField(_('actif'), default=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modifié le'), auto_now=True)
    
    # ========== PAIEMENT ET LIMITES ==========
    is_paid = models.BooleanField(_('payé'), default=False)
    max_guests_allowed = models.PositiveIntegerField(_('nombre max d\'invités'), default=400)
    max_collaborators_allowed = models.PositiveIntegerField(_('nombre max de co-organisateurs'), default=5)
    # payment_request = models.ForeignKey(
    #     'payments.PaymentRequest',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='events',
    #     verbose_name=_('demande de paiement'),
    # )
    
    class Meta:
        verbose_name = _('événement')
        verbose_name_plural = _('événements')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def generate_uuid_token(self):
        return uuid.uuid4().hex[:12]
    
    def save(self, *args, **kwargs):
        if not self.rsvp_token:
            self.rsvp_token = self.generate_uuid_token()
        if not self.coorganizer_token:
            self.coorganizer_token = self.generate_uuid_token()
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def get_rsvp_url(self):
        return f'/events/{self.slug}/rsvp/{self.rsvp_token}/'

    def get_coorganizer_url(self):
        return f'/events/{self.slug}/join/{self.coorganizer_token}/'
    
    def get_google_calendar_link(self):
        if not self.date:
            return ""
        start_date = self.date.strftime("%Y%m%d")
        if self.time:
            start_date += f"T{self.time.strftime('%H%M%S')}"
        else:
            start_date += "T000000"
        end_date = self.date.strftime("%Y%m%d")
        if self.time:
            end_time = (datetime.combine(self.date, self.time) + timedelta(hours=2)).time()
            end_date += f"T{end_time.strftime('%H%M%S')}"
        else:
            end_date += "T020000"
        params = {
            'action': 'TEMPLATE',
            'text': f"Événement: {self.name}",
            'dates': f"{start_date}/{end_date}",
            'details': self.description or "",
            'location': self.location,
            'trp': 'false',
        }
        query_string = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        return f"https://calendar.google.com/calendar/render?{query_string}"
    
    def total_invited_guests(self):
        return self.invited_guests.count()
    
    def total_responses(self):
        return self.responses.count()
    
    def verified_responses(self):
        return self.responses.filter(verification_status='verified').count()
    
    def unverified_responses(self):
        return self.responses.filter(verification_status='unverified').count()
    
    def attendance_rate(self):
        verified = self.verified_responses()
        if verified == 0:
            return 0
        attending = self.responses.filter(verification_status='verified', will_attend=True).count()
        return round((attending / verified) * 100, 1)
    
    def will_attend_count(self):
        return self.responses.filter(verification_status='verified', will_attend=True).count()
    
    def total_expected_guests(self):
        total = 0
        for response in self.responses.filter(verification_status='verified', will_attend=True):
            total += response.number_of_guests
        return total

class EventCollaborator(models.Model):
    """
    Modèle pour les co-organisateurs d'un événement
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        ACCEPTED = 'accepted', _('Accepté')
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='collaborators',
        verbose_name=_('événement'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('utilisateur'),
    )
    invitation_token = models.CharField(_('token d\'invitation'), max_length=50, unique=True)
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    can_scan = models.BooleanField(_('peut scanner'), default=False)

    invited_at = models.DateTimeField(_('invité le'), auto_now_add=True)
    accepted_at = models.DateTimeField(_('accepté le'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('co-organisateur')
        verbose_name_plural = _('co-organisateurs')
        unique_together = ['event', 'user']
    
    def save(self, *args, **kwargs):
        if not self.invitation_token:
            # Token plus long pour les invitations
            self.invitation_token = secrets.token_urlsafe(32)[:50]
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} - {self.event.name}"
    
    def accept(self):
        """Accepte l'invitation"""
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
        
# ========== NOUVEAU : TABLE ==========
class Table(models.Model):
    """Table pour un événement"""
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='tables',
        verbose_name=_('table'),
    )
    number = models.CharField(_('numéro'), max_length=10)
    name = models.CharField(_('nom'), max_length=100, blank=True)
    capacity = models.PositiveIntegerField(_('capacité'), default=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('table')
        verbose_name_plural = _('tables')
        unique_together = [('event', 'number')]
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} - {self.event.name}"