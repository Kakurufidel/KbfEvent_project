from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import unicodedata
import logging
import uuid
logger = logging.getLogger(__name__)


class InvitedGuest(models.Model):
    """
    Liste des invités pré-enregistrés par l'organisateur.
    Ces personnes sont considérées comme des invités officiels.
    """
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='invited_guests',
        verbose_name=_('événement'),
    )
    name = models.CharField(_('nom'), max_length=200)
    email = models.EmailField(_('email'), blank=True)
    phone = models.CharField(_('téléphone'), max_length=20, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('créé par'),
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('invité pré-enregistré')
        verbose_name_plural = _('invités pré-enregistrés')
        unique_together = ['event', 'email']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.event.name})"
    
    @property
    def has_responded(self):
        """Vérifie si cet invité a déjà répondu"""
        normalized_name = GuestResponse.normalize_name(self.name)
        return GuestResponse.objects.filter(
            event=self.event,
            verification_status='verified'
        ).exists()
        # Note: La vérification se fait par nom normalisé dans la méthode
        # verify_against_invited_list de GuestResponse


class GuestResponse(models.Model):
    """
    Réponse d'un invité (RSVP).
    Peut provenir d'un invité officiel (verified) ou d'une personne non invitée (unverified).
    """
    
    class DrinkChoice(models.TextChoices):
        VIN = 'vin', _('Vin')
        BIERE = 'biere', _('Bière')
        SOFT = 'soft', _('Soft')
        OTHER = 'other', _('Autre')
    
    class VerificationStatus(models.TextChoices):
        VERIFIED = 'verified', _('Vérifié - Invité officiel')
        UNVERIFIED = 'unverified', _('Non vérifié - Personne non invitée')
    
    # ========== RELATIONS ==========
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('événement'),
    )
    
    # ========== INFORMATIONS RÉPONDANT ==========
    name = models.CharField(_('nom complet'), max_length=200)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=20, blank=True)
    
    # ========== RÉPONSE À L'INVITATION ==========
    will_attend = models.BooleanField(_('sera présent(e)'), default=True)
    number_of_guests = models.PositiveIntegerField(_('nombre de personnes'), default=1)
    
    # ========== OPTIONS ==========
    drink_choice = models.CharField(
        _('choix de boisson'),
        max_length=20,
        choices=DrinkChoice.choices,
        blank=True,
    )
    drink_other = models.CharField(_('autre boisson'), max_length=100, blank=True)
    is_vegan = models.BooleanField(_('végétarien/végétalien'), default=False)
    special_notes = models.TextField(_('notes spéciales'), blank=True)
    
    # ========== VÉRIFICATION ==========
    verification_status = models.CharField(
        _('statut de vérification'),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        help_text=_('Vérifié = la personne était dans la liste des invités pré-enregistrés')
    )
    
    # ========== MÉTADONNÉES ==========
    submitted_at = models.DateTimeField(_('soumis le'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('adresse IP'), null=True, blank=True)
    
    # ========== RAPPELS ==========
    reminder_sent = models.BooleanField(_('rappel envoyé'), default=False)
    reminder_sent_at = models.DateTimeField(_('rappel envoyé le'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('réponse d\'invité')
        verbose_name_plural = _('réponses des invités')
        ordering = ['-submitted_at']
        unique_together = ['event', 'email']  # Une réponse par email par événement
    
    def __str__(self):
        return f"{self.name} - {self.event.name} ({self.get_verification_status_display()})"
    
    # ========== MÉTHODES STATIQUES ==========
    
    @staticmethod
    def normalize_name(text):
        """
        Normalise un nom pour la comparaison:
        - Convertit en minuscules
        - Supprime les accents
        - Supprime les espaces superflus
        """
        if not text:
            return ""
        text = text.lower().strip()
        # Normalisation Unicode pour supprimer les accents
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        return text
    
    # ========== LOGIQUE MÉTIER ==========
    
    def verify_against_invited_list(self):
        """
        Vérifie si cette réponse correspond à un invité pré-enregistré.
        
        Returns:
            bool: True si correspondance trouvée, False sinon
        
        Logique:
            1. Normalise le nom du répondant
            2. Compare avec chaque nom normalisé des invités pré-enregistrés
            3. Si correspondance → status = 'verified'
            4. Sauvegarde automatiquement
        """
        normalized_response_name = self.normalize_name(self.name)
        
        for invited_guest in self.event.invited_guests.all():
            if self.normalize_name(invited_guest.name) == normalized_response_name:
                self.verification_status = 'verified'
                self.save(update_fields=['verification_status'])
                logger.info(f"Réponse vérifiée: {self.name} correspond à l'invité {invited_guest.name}")
                return True
        
        logger.warning(f"Réponse non vérifiée: {self.name} n'est pas dans la liste des invités")
        return False
    
    def send_confirmation_email(self):
        """
        Envoie un email de confirmation au répondant.
        L'email est différent selon que la personne est vérifiée ou non.
        
        Returns:
            bool: True si l'email a été envoyé, False sinon
        """
        event = self.event
        
        # Choisir le template selon le statut de vérification
        if self.verification_status == 'verified':
            template_name = 'emails/rsvp_confirmation_verified.html'
            subject = f"Confirmation de votre présence - {event.name}"
        else:
            template_name = 'emails/rsvp_confirmation_unverified.html'
            subject = f"Nous avons bien reçu votre réponse - {event.name}"
        
        context = {
            'guest_name': self.name,
            'event': event,
            'response': self,
            'google_calendar_link': event.get_google_calendar_link(),
            'google_maps_link': event.google_maps_link,
            'is_verified': self.verification_status == 'verified',
        }
        
        try:
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=event.sender_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email de confirmation envoyé à {self.email}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email à {self.email}: {str(e)}")
            return False
    
    def send_reminder(self):
        """
        Envoie un email de rappel (différent de la confirmation)
        """
        if self.reminder_sent:
            return False
        
        event = self.event
        
        context = {
            'guest_name': self.name,
            'event': event,
            'response': self,
            'google_calendar_link': event.get_google_calendar_link(),
            'google_maps_link': event.google_maps_link,
        }
        
        try:
            html_message = render_to_string('emails/rsvp_reminder.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"Rappel: {event.name} - Merci de confirmer votre présence",
                message=plain_message,
                from_email=event.sender_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            self.reminder_sent = True
            self.reminder_sent_at = timezone.now()
            self.save(update_fields=['reminder_sent', 'reminder_sent_at'])
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rappel à {self.email}: {str(e)}")
            return False
    
    # ========== PROPRIÉTÉS UTILITAIRES ==========
    
    @property
    def is_verified(self):
        """Alias pour verification_status == 'verified'"""
        return self.verification_status == 'verified'
    
    @property
    def drink_display(self):
        """Retourne l'affichage lisible du choix de boisson"""
        if self.drink_choice == 'other':
            return self.drink_other or "Autre (non précisé)"
        return self.get_drink_choice_display() or "Non spécifié"
    
    @property
    def matched_invited_guest(self):
        """
        Retourne l'invité pré-enregistré correspondant (si vérifié)
        """
        if not self.is_verified:
            return None
        
        normalized_name = self.normalize_name(self.name)
        for guest in self.event.invited_guests.all():
            if self.normalize_name(guest.name) == normalized_name:
                return guest
        return None

class Guest(models.Model):
    """Modèle pour les invités """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        CONFIRMED = 'confirmed', _('Confirmé')
        DECLINED = 'declined', _('Décliné')
    
    first_name = models.CharField(_('prénom'), max_length=150)
    last_name = models.CharField(_('nom'), max_length=150)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=30, blank=True)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='guests',
        verbose_name=_('événement'),
    )
    drink_choice = models.CharField(
        _('choix de boisson'),
        max_length=200,
        blank=True,
        null=True,
    )
    drink_other = models.TextField(
        _('autre boisson'),
        blank=True,
        null=True,
    )
    is_accompanied = models.BooleanField(
        _('accompagné'),
        default=False,
    )
    companion_drink_choice = models.CharField(
        _('choix boisson accompagnant'),
        max_length=200,
        blank=True,
        null=True,
    )
    companion_drink_other = models.TextField(
        _('autre boisson accompagnant'),
        blank=True,
        null=True,
    )
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    unique_token = models.UUIDField(
        _('token unique'),
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('invité')
        verbose_name_plural = _('invités')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_rsvp_link(self, request=None):
        from django.urls import reverse
        relative_url = reverse('guests:rsvp', kwargs={'token': self.unique_token})
        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    def confirm(self):
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status'])

    def decline(self):
        self.status = self.Status.DECLINED
        self.save(update_fields=['status'])