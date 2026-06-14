# apps/guests/models.py
import uuid
import unicodedata
import logging
from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse

logger = logging.getLogger(__name__)


class InvitedGuest(models.Model):
    """
    Liste des invités pré-enregistrés par l'organisateur (import Excel).
    Ces personnes sont considérées comme des invités officiels.
    """
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='invited_guests',
        verbose_name=_('événement'),
    )
    first_name = models.CharField(_('prénom'), max_length=100)
    last_name = models.CharField(_('nom'), max_length=100)
    middle_name = models.CharField(_('postnom'), max_length=100, blank=True)
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
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.event.name})"

    def get_full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


class GuestResponse(models.Model):
    """
    Réponse d'un invité (RSVP) via le formulaire public.
    """
    
    class DrinkChoice(models.TextChoices):
        VIN = 'vin', _('Vin')
        BIERE = 'biere', _('Bière')
        SOFT = 'soft', _('Soft')
        JUS = 'jus', _('Jus')
        EAU = 'eau', _('Eau')
        OTHER = 'other', _('Autre')
    
    class VerificationStatus(models.TextChoices):
        VERIFIED = 'verified', _('Vérifié - Invité officiel')
        UNVERIFIED = 'unverified', _('Non vérifié')
    
    # Relations
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('événement'),
    )
    
    # Informations répondant
    first_name = models.CharField(_('prénom'), max_length=100)
    last_name = models.CharField(_('nom'), max_length=100)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=20, blank=True)
    
    # Réponse
    will_attend = models.BooleanField(_('sera présent(e)'), default=True)
    number_of_guests = models.PositiveIntegerField(_('nombre de personnes'), default=1)
    
    # Accompagnement
    is_accompanied = models.BooleanField(_('accompagné(e)'), default=False)
    companion_name = models.CharField(_('nom de l\'accompagnant'), max_length=200, blank=True)
    companion_first_name = models.CharField(_('prénom accompagnant'), max_length=100, blank=True)
    companion_last_name = models.CharField(_('nom accompagnant'), max_length=100, blank=True)
    
    # Boissons
    drink_choice = models.CharField(
        _('choix de boisson'),
        max_length=20,
        choices=DrinkChoice.choices,
        blank=True,
    )
    drink_other = models.CharField(_('autre boisson'), max_length=100, blank=True)
    companion_drink_choice = models.CharField(
        _('boisson accompagnant'),
        max_length=20,
        choices=DrinkChoice.choices,
        blank=True,
    )
    companion_drink_other = models.CharField(_('autre boisson accompagnant'), max_length=100, blank=True)
    
    # Végétarien / notes
    is_vegan = models.BooleanField(_('végétarien/végétalien'), default=False)
    special_notes = models.TextField(_('notes spéciales'), blank=True)
    
    # Vérification
    verification_status = models.CharField(
        _('statut de vérification'),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    
    # Métadonnées
    submitted_at = models.DateTimeField(_('soumis le'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('adresse IP'), null=True, blank=True)
    
    # Rappels
    reminder_sent = models.BooleanField(_('rappel envoyé'), default=False)
    reminder_sent_at = models.DateTimeField(_('rappel envoyé le'), null=True, blank=True)
    
    # Token pour invitation électronique
    invitation_token = models.UUIDField(
        _('token invitation'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    class Meta:
        verbose_name = _('réponse d\'invité')
        verbose_name_plural = _('réponses des invités')
        ordering = ['-submitted_at']
        unique_together = ['event', 'email']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event.name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_companion_full_name(self):
        if self.companion_first_name and self.companion_last_name:
            return f"{self.companion_first_name} {self.companion_last_name}"
        return self.companion_name or ""

    @staticmethod
    def normalize_name(text):
        """Normalise un nom pour la comparaison."""
        if not text:
            return ""
        text = text.lower().strip()
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        return text

    def verify_against_invited_list(self):
        """Vérifie si cette réponse correspond à un invité pré-enregistré."""
        normalized_first = self.normalize_name(self.first_name)
        normalized_last = self.normalize_name(self.last_name)
        
        for invited in self.event.invited_guests.all():
            if (self.normalize_name(invited.first_name) == normalized_first and
                self.normalize_name(invited.last_name) == normalized_last):
                self.verification_status = 'verified'
                self.save(update_fields=['verification_status'])
                logger.info(f"Réponse vérifiée: {self.get_full_name()}")
                return True
        
        # Vérification par email si noms ne correspondent pas
        for invited in self.event.invited_guests.all():
            if invited.email and invited.email.lower() == self.email.lower():
                self.verification_status = 'verified'
                self.save(update_fields=['verification_status'])
                logger.info(f"Réponse vérifiée par email: {self.get_full_name()}")
                return True
        
        logger.warning(f"Réponse non vérifiée: {self.get_full_name()}")
        return False

    def send_confirmation_email(self):
        """Envoie l'invitation électronique avec lien Google Agenda."""
        event = self.event
        
        if self.verification_status == 'verified':
            template_name = 'emails/rsvp_confirmation_verified.html'
            subject = f"✅ Confirmation - {event.name}"
        else:
            template_name = 'emails/rsvp_confirmation_unverified.html'
            subject = f"📩 Nous avons reçu votre réponse - {event.name}"
        
        # Construire le lien d'invitation électronique
        invitation_link = self.get_invitation_link()
        
        context = {
            'guest_name': self.get_full_name(),
            'event': event,
            'response': self,
            'invitation_link': invitation_link,
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
            logger.error(f"Erreur envoi email à {self.email}: {str(e)}")
            return False

    def send_reminder(self):
        """Envoie un email de rappel (J-7 ou J-2)."""
        if self.reminder_sent:
            return False
        
        event = self.event
        
        context = {
            'guest_name': self.get_full_name(),
            'event': event,
            'response': self,
            'google_calendar_link': event.get_google_calendar_link(),
            'google_maps_link': event.google_maps_link,
        }
        
        try:
            html_message = render_to_string('emails/rsvp_reminder.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"📅 Rappel: {event.name} - Confirmez votre présence",
                message=plain_message,
                from_email=event.sender_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            self.reminder_sent = True
            self.reminder_sent_at = timezone.now()
            self.save(update_fields=['reminder_sent', 'reminder_sent_at'])
            logger.info(f"Rappel envoyé à {self.email}")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi rappel à {self.email}: {str(e)}")
            return False

    def get_invitation_link(self, request=None):
        """Lien pour télécharger l'invitation électronique."""
        if request:
            return request.build_absolute_uri(
                reverse('guests:invitation_pdf', args=[str(self.invitation_token)])
            )
        return reverse('guests:invitation_pdf', args=[str(self.invitation_token)])

    @property
    def is_verified(self):
        return self.verification_status == 'verified'
    
    @property
    def drink_display(self):
        if self.drink_choice == 'other':
            return self.drink_other or "Autre"
        return self.get_drink_choice_display() or "Non spécifié"
    
    @property
    def companion_drink_display(self):
        if self.companion_drink_choice == 'other':
            return self.companion_drink_other or "Autre"
        return self.get_companion_drink_choice_display() or "Non spécifié"