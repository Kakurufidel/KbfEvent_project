# apps/guests/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import GuestResponse, InvitedGuest


class RSVPForm(forms.ModelForm):
    """Formulaire public pour répondre à une invitation"""
    
    drink_other = forms.CharField(
        label=_('Autre boisson'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Précisez votre boisson (ex: Amarula, Whisky...)'
        })
    )
    companion_drink_other = forms.CharField(
        label=_('Autre boisson pour accompagnant'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Précisez la boisson de l\'accompagnant'
        })
    )
    
    class Meta:
        model = GuestResponse
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'will_attend', 'number_of_guests',
            'is_accompanied', 'companion_first_name', 'companion_last_name',
            'drink_choice', 'is_vegan', 'special_notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'votre@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+243 XXX XXX XXX (optionnel)'
            }),
            'will_attend': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'number_of_guests': forms.NumberInput(attrs={
                'min': 1,
                'max': 10,
                'class': 'form-control'
            }),
            'drink_choice': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_accompanied': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'is_accompanied_checkbox'
            }),
            'companion_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom de l\'accompagnant'
            }),
            'companion_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'accompagnant'
            }),
            'is_vegan': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'special_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Allergies, régime alimentaire, besoins spécifiques...'
            }),
        }
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'email': _('Email'),
            'phone': _('Téléphone'),
            'will_attend': _('Je serai présent(e)'),
            'number_of_guests': _('Nombre de personnes (incluant vous)'),
            'drink_choice': _('Boisson préférée'),
            'is_accompanied': _('Je serai accompagné(e)'),
            'companion_first_name': _('Prénom de l\'accompagnant'),
            'companion_last_name': _('Nom de l\'accompagnant'),
            'is_vegan': _('Option végétarienne/végétalienne'),
            'special_notes': _('Notes spéciales'),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les choix de boissons selon l'événement
        if self.event and self.event.drink_options:
            choices = [('', _('Sélectionnez une boisson'))]
            choices.extend([(d.lower(), d) for d in self.event.drink_options])
            choices.append(('other', _('Autre')))
            self.fields['drink_choice'].choices = choices
        
        # Rendre certains champs optionnels
        self.fields['phone'].required = False
        self.fields['special_notes'].required = False
        self.fields['companion_first_name'].required = False
        self.fields['companion_last_name'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Vérification boisson "autre"
        if cleaned_data.get('drink_choice') == 'other':
            if not cleaned_data.get('drink_other'):
                self.add_error('drink_other', _('Veuillez préciser votre boisson'))
        
        # Vérification accompagnement
        if cleaned_data.get('is_accompanied'):
            if not cleaned_data.get('companion_first_name'):
                self.add_error('companion_first_name', _('Veuillez indiquer le prénom de l\'accompagnant'))
            if not cleaned_data.get('companion_last_name'):
                self.add_error('companion_last_name', _('Veuillez indiquer le nom de l\'accompagnant'))
        
        # Vérification email
        email = cleaned_data.get('email')
        if email and self.event:
            # Vérifier si cet email a déjà répondu
            if GuestResponse.objects.filter(event=self.event, email=email).exists():
                self.add_error('email', _('Cet email a déjà répondu à cette invitation'))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event = self.event
        
        # Gestion des boissons "autre"
        if self.cleaned_data.get('drink_choice') == 'other':
            instance.drink_choice = 'other'
            instance.drink_other = self.cleaned_data.get('drink_other', '')
        
        # Gestion de l'accompagnement
        if instance.is_accompanied:
            instance.companion_name = f"{self.cleaned_data.get('companion_first_name', '')} {self.cleaned_data.get('companion_last_name', '')}"
        
        if commit:
            instance.save()
            # Vérification automatique après sauvegarde
            instance.verify_against_invited_list()
            # Envoi email de confirmation
            instance.send_confirmation_email()
        
        return instance


class InvitedGuestForm(forms.ModelForm):
    """Formulaire pour ajouter manuellement un invité pré-enregistré"""
    
    class Meta:
        model = InvitedGuest
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postnom (optionnel)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+243 XXX XXX XXX'
            }),
        }


class GuestBulkImportForm(forms.Form):
    """Formulaire pour importer un fichier Excel d'invités"""
    excel_file = forms.FileField(
        label=_('Fichier Excel'),
        help_text=_('Format attendu: Prénom, Nom, Postnom (optionnel), Email, Téléphone'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx, .xls, .csv'
        })
    )