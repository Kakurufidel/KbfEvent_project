from django import forms
from .models import Event


class EventForm(forms.ModelForm):
    """Formulaire pour créer/modifier un événement"""
    
    # Champ spécial pour les boissons (JSON transformé en texte)
    drink_options_text = forms.CharField(
        label='Options de boissons',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Vin, Bière, Soft, Jus...',
            'class': 'w-full px-3 py-2 border rounded-lg'
        }),
        help_text='Séparez les boissons par des virgules'
    )
    
    class Meta:
        model = Event
        fields = [
            'name', 'event_type', 'event_type_other', 'description',
            'date', 'time', 'location', 'google_maps_link',
            'dress_code', 'reminder_message', 'sender_email'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Nom de l\'événement'}),
            'event_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'event_type_other': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Précisez le type'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Description de l\'événement'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Adresse du lieu'}),
            'google_maps_link': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'https://maps.google.com/...'}),
            'dress_code': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Code vestimentaire'}),
            'reminder_message': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'Message de rappel pour les invités'}),
            'sender_email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg', 'placeholder': 'noreply@example.com'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remplir le champ texte des boissons si l'instance existe
        if self.instance and self.instance.pk and self.instance.drink_options:
            self.initial['drink_options_text'] = ', '.join(self.instance.drink_options)
        # Rendre certains champs optionnels
        self.fields['event_type_other'].required = False
        self.fields['google_maps_link'].required = False
        self.fields['dress_code'].required = False
        self.fields['reminder_message'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get('event_type')
        event_type_other = cleaned_data.get('event_type_other')
        
        if event_type == 'other' and not event_type_other:
            self.add_error('event_type_other', 'Veuillez préciser le type d\'événement')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarde en convertissant le texte des boissons en JSON"""
        instance = super().save(commit=False)
        
        # Convertir le texte des boissons en liste
        drink_text = self.cleaned_data.get('drink_options_text', '')
        if drink_text:
            instance.drink_options = [d.strip() for d in drink_text.split(',') if d.strip()]
        else:
            instance.drink_options = []
        
        if commit:
            instance.save()
        return instance