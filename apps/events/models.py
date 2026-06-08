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
    # Utilisation de uuid pour générer des tokens uniques
    rsvp_token = models.CharField(_('token RSVP'), max_length=36, unique=True, blank=True)
    coorganizer_token = models.CharField(_('token co-organisateur'), max_length=36, unique=True, blank=True)
    slug = models.SlugField(_('slug'), unique=True, max_length=200, blank=True)
    
    # ========== STATUT ==========
    is_active = models.BooleanField(_('actif'), default=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modifié le'), auto_now=True)
    
    class Meta:
        verbose_name = _('événement')
        verbose_name_plural = _('événements')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def generate_uuid_token(self):
        """Génère un token UUID simple (sans tirets)"""
        return uuid.uuid4().hex[:12]  # Prend les 12 premiers caractères hex
    
    def save(self, *args, **kwargs):
        """Génération automatique des tokens et du slug"""
        # Générer les tokens s'ils n'existent pas
        if not self.rsvp_token:
            self.rsvp_token = self.generate_uuid_token()
        if not self.coorganizer_token:
            self.coorganizer_token = self.generate_uuid_token()
        
        # Générer le slug à partir du nom
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    # ========== URLS PUBLIQUES ==========
    
    def get_rsvp_url(self):
        """URL pour le formulaire RSVP des invités"""
        # Construction directe sans reverse
        return f'/events/{self.slug}/rsvp/{self.rsvp_token}/'

    def get_coorganizer_url(self):
        """URL pour inviter des co-organisateurs"""
        return f'/events/{self.slug}/join/{self.coorganizer_token}/'
    def get_google_calendar_link(self):
        """Génère le lien Google Calendar"""
        if not self.date:
            return ""
        
        start_date = self.date.strftime("%Y%m%d")
        if self.time:
            start_date += f"T{self.time.strftime('%H%M%S')}"
        else:
            start_date += "T000000"
        
        # Durée par défaut: 2 heures
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
        
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f"https://calendar.google.com/calendar/render?{quote(query_string)}"
    
    # ========== STATISTIQUES ==========
    
    def total_invited_guests(self):
        """Nombre total d'invités pré-enregistrés"""
        return self.invited_guests.count()
    
    def total_responses(self):
        """Nombre total de réponses reçues"""
        return self.responses.count()
    
    def verified_responses(self):
        """Nombre de réponses vérifiées (invités officiels)"""
        return self.responses.filter(verification_status='verified').count()
    
    def unverified_responses(self):
        """Nombre de réponses non vérifiées (personnes non invitées)"""
        return self.responses.filter(verification_status='unverified').count()
    
    def attendance_rate(self):
        """Taux de présence calculé sur les réponses vérifiées"""
        verified = self.verified_responses()
        if verified == 0:
            return 0
        attending = self.responses.filter(
            verification_status='verified',
            will_attend=True
        ).count()
        return round((attending / verified) * 100, 1)
    
    def will_attend_count(self):
        """Nombre de personnes qui ont dit oui (invités vérifiés)"""
        return self.responses.filter(
            verification_status='verified',
            will_attend=True
        ).count()
    
    def total_expected_guests(self):
        """Nombre total de personnes attendues (incluant accompagnants)"""
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