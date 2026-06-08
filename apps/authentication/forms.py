from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User


class LoginForm(AuthenticationForm):
    """Formulaire de connexion standard"""
    username = forms.CharField(label=_('Email ou nom d\'utilisateur'), widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg',
        'placeholder': 'email@example.com ou username'
    }))
    password = forms.CharField(label=_('Mot de passe'), widget=forms.PasswordInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg',
        'placeholder': '••••••••'
    }))


class RegisterForm(UserCreationForm):
    """Formulaire d'inscription simplifié"""
    email = forms.EmailField(label=_('Email'), widget=forms.EmailInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg',
        'placeholder': 'votre@email.com'
    }))
    phone = forms.CharField(label=_('Téléphone'), required=False, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg',
        'placeholder': '+33 6 12 34 56 78'
    }))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg',
                'placeholder': 'Nom d\'utilisateur'
            }),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user