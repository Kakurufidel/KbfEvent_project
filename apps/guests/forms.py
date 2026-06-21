from django import forms
from django.utils.translation import gettext_lazy as _
from .models import GuestResponse, InvitedGuest


class RSVPForm(forms.ModelForm):
    """Formulaire public pour répondre à une invitation"""
    
    attendance = forms.ChoiceField(
        label=_('Souhaitez-vous participer ?'),
        choices=[('yes', _('Oui, je serai présent(e)')), ('no', _('Non, je ne pourrai pas venir'))],
        widget=forms.RadioSelect(attrs={'class': 'flex gap-4'})
    )
    
    # Champ "nombre d'accompagnants" (non présent dans le modèle)
    number_of_companions = forms.IntegerField(
        label=_("Nombre d'accompagnants"),
        min_value=0,
        max_value=10,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
            'placeholder': '0'
        })
    )
    
    drink_other = forms.CharField(
        label=_('Autre boisson'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
            'placeholder': 'Précisez votre boisson'
        })
    )
    companion_drink_other = forms.CharField(
        label=_('Autre boisson pour accompagnant'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
            'placeholder': 'Précisez la boisson de l\'accompagnant'
        })
    )
    
    class Meta:
        model = GuestResponse
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'is_accompanied', 'companion_first_name', 'companion_last_name',
            'drink_choice', 'companion_drink_choice',
            'is_vegan', 'special_notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Votre prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Votre nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'votre@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': '+243 XXX XXX XXX (optionnel)'
            }),
            'drink_choice': forms.Select(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400'
            }),
            'companion_drink_choice': forms.Select(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400'
            }),
            'is_accompanied': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-purple-500 focus:ring-purple-500',
                # 'id': 'is_accompanied_checkbox'
            }),
            'companion_first_name': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Prénom de l\'accompagnant (optionnel)'
            }),
            'companion_last_name': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Nom de l\'accompagnant (optionnel)'
            }),
            'is_vegan': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-purple-500 focus:ring-purple-500'
            }),
            'special_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Allergies, régime alimentaire, besoins spécifiques...'
            }),
        }
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'email': _('Email'),
            'phone': _('Téléphone'),
            'drink_choice': _('Boisson préférée'),
            'companion_drink_choice': _('Boisson de l\'accompagnant'),
            'is_accompanied': _('Je serai accompagné(e)'),
            'companion_first_name': _('Prénom de l\'accompagnant (optionnel)'),
            'companion_last_name': _('Nom de l\'accompagnant (optionnel)'),
            'is_vegan': _('Option végétarienne/végétalienne'),
            'special_notes': _('Notes spéciales'),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les choix de boissons
        if self.event and self.event.drink_options:
            choices = [('', _('Sélectionnez une boisson'))]
            choices.extend([(d.lower(), d) for d in self.event.drink_options])
            choices.append(('other', _('Autre')))
            self.fields['drink_choice'].choices = choices
            self.fields['companion_drink_choice'].choices = choices
        
        # Champs optionnels
        self.fields['phone'].required = False
        self.fields['special_notes'].required = False
        self.fields['companion_first_name'].required = False
        self.fields['companion_last_name'].required = False
        self.fields['number_of_companions'].required = False
        
        # Pré-remplir attendance
        if self.instance and self.instance.pk:
            self.fields['attendance'].initial = 'yes' if self.instance.will_attend else 'no'
            # Pré-remplir le nombre d'accompagnants
            if self.instance.number_of_guests > 0:
                self.fields['number_of_companions'].initial = self.instance.number_of_guests - 1
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifier boisson "autre" pour l'invité
        if cleaned_data.get('drink_choice') == 'other':
            if not cleaned_data.get('drink_other'):
                self.add_error('drink_other', _('Veuillez préciser votre boisson'))
        
        # Vérifier accompagnement
        is_accompanied = cleaned_data.get('is_accompanied')
        if is_accompanied:
            # Boisson de l'accompagnant obligatoire
            companion_drink = cleaned_data.get('companion_drink_choice')
            if not companion_drink:
                self.add_error('companion_drink_choice', _('Veuillez indiquer la boisson de l\'accompagnant'))
            elif companion_drink == 'other':
                if not cleaned_data.get('companion_drink_other'):
                    self.add_error('companion_drink_other', _('Veuillez préciser la boisson de l\'accompagnant'))
            
            # Nombre d'accompagnants : si coché mais nombre = 0, on force 1 ?
            # On peut laisser 0 (signifie qu'il n'y a pas d'accompagnant, mais la case est cochée => incohérence)
            # On va exiger au moins 1 si la case est cochée
            companions = cleaned_data.get('number_of_companions')
            if companions is None or companions < 1:
                self.add_error('number_of_companions', _('Veuillez indiquer le nombre d\'accompagnants (au moins 1)'))
        else:
            # Si non accompagné, on met le nombre d'accompagnants à 0
            cleaned_data['number_of_companions'] = 0
        
        # Vérifier email en double
        email = cleaned_data.get('email')
        if email and self.event and self.event.pk:
            qs = GuestResponse.objects.filter(event=self.event, email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('email', _('Cet email a déjà répondu à cette invitation'))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event = self.event
        
        # Attendance -> will_attend
        attendance = self.cleaned_data.get('attendance')
        instance.will_attend = (attendance == 'yes')
        
        # Calcul du nombre total de personnes
        companions = self.cleaned_data.get('number_of_companions') or 0
        instance.number_of_guests = 1 + companions
        
        # Gestion des boissons "autre"
        if self.cleaned_data.get('drink_choice') == 'other':
            instance.drink_choice = 'other'
            instance.drink_other = self.cleaned_data.get('drink_other', '')
        else:
            instance.drink_other = ''
        
        if self.cleaned_data.get('companion_drink_choice') == 'other':
            instance.companion_drink_choice = 'other'
            instance.companion_drink_other = self.cleaned_data.get('companion_drink_other', '')
        else:
            instance.companion_drink_other = ''
        
        # Nom de l'accompagnant (fusion)
        if instance.is_accompanied:
            first = self.cleaned_data.get('companion_first_name', '').strip()
            last = self.cleaned_data.get('companion_last_name', '').strip()
            instance.companion_name = f"{first} {last}".strip()
        else:
            instance.companion_name = ''
        
        if commit:
            instance.save()
            instance.verify_against_invited_list()
            instance.send_confirmation_email()
        
        return instance
    
        if instance.email:
            invited_guests = InvitedGuest.objects.filter(
            event=self.event,
            email__iexact=instance.email
        ).first()
            
        if invited_guests and invited_guests.table:
            instance.table = invited_guests.table

        if commit:
            instance.save()
            instance.verify_against_invited_list()
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