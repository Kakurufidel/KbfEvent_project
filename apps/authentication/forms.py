from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User


class LoginForm(AuthenticationForm):
    """Formulaire de connexion - accepte email ou username"""
    username = forms.CharField(label=_('Email ou nom d\'utilisateur'), widget=forms.TextInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': 'email@example.com ou pseudo'
    }))
    password = forms.CharField(label=_('Mot de passe'), widget=forms.PasswordInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': '••••••••'
    }))


class RegisterForm(UserCreationForm):
    """Formulaire d'inscription - SANS champ username (auto-généré)"""
    
    email = forms.EmailField(label=_('Email'), widget=forms.EmailInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': 'votre@email.com'
    }))
    
    first_name = forms.CharField(label=_('Prénom'), required=True, widget=forms.TextInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': 'Votre prénom'
    }))
    
    last_name = forms.CharField(label=_('Nom'), required=True, widget=forms.TextInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': 'Votre nom'
    }))
    
    phone = forms.CharField(label=_('Téléphone'), required=False, widget=forms.TextInput(attrs={
        'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
        'placeholder': '+225 05 55 55 55'
    }))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('Cet email est déjà utilisé.'))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data.get('phone', '')
        
        # Générer un username automatiquement
        base_username = self.cleaned_data['email'].split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        
        if commit:
            user.save()
        return user