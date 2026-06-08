from django import forms
from .models import GuestResponse, InvitedGuest


class RSVPForm(forms.ModelForm):
    """Formulaire public pour répondre à une invitation"""
    
    drink_other = forms.CharField(
        label='Autre boisson',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Précisez votre boisson'})
    )
    
    class Meta:
        model = GuestResponse
        fields = [
            'name', 'email', 'phone', 'will_attend', 'number_of_guests',
            'drink_choice', 'is_vegan', 'special_notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Votre nom complet'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'votre@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Optionnel'}),
            'will_attend': forms.CheckboxInput(attrs={'class': 'mr-2'}),
            'number_of_guests': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'drink_choice': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'is_vegan': forms.CheckboxInput(attrs={'class': 'mr-2'}),
            'special_notes': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Régime alimentaire, allergies, etc.'}),
        }
        labels = {
            'will_attend': 'Je serai présent(e)',
            'number_of_guests': 'Nombre de personnes (incluant vous)',
            'drink_choice': 'Boisson préférée',
            'is_vegan': 'Option végétarienne/végétalienne',
            'special_notes': 'Notes spéciales',
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les choix de boissons selon l'événement
        if self.event and self.event.drink_options:
            choices = [('', 'Sélectionnez une boisson')]
            choices.extend([(d.lower(), d) for d in self.event.drink_options])
            choices.append(('other', 'Autre'))
            self.fields['drink_choice'].choices = choices
    
    def clean(self):
        cleaned_data = super().clean()
        drink_choice = cleaned_data.get('drink_choice')
        drink_other = cleaned_data.get('drink_other')
        
        if drink_choice == 'other' and not drink_other:
            self.add_error('drink_other', 'Veuillez préciser votre boisson')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarde avec gestion de la boisson 'autre'"""
        instance = super().save(commit=False)
        instance.event = self.event
        
        if self.cleaned_data.get('drink_choice') == 'other':
            instance.drink_choice = 'other'
            instance.drink_other = self.cleaned_data.get('drink_other', '')
        
        if commit:
            instance.save()
            # Vérification automatique après sauvegarde
            instance.verify_against_invited_list()
            # Envoi email de confirmation
            instance.send_confirmation_email()
        
        return instance


class InvitedGuestForm(forms.ModelForm):
    """Formulaire pour ajouter manuellement un invité"""
    
    class Meta:
        model = InvitedGuest
        fields = ['name', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Nom complet'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': '+123456789'}),
        }
        
GuestRSVPForm = RSVPForm
