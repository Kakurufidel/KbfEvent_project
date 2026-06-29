from django import forms
from django.utils.translation import gettext_lazy as _
from .models import BeveragePack


class BeveragePackForm(forms.ModelForm):
    class Meta:
        model = BeveragePack
        fields = ['drink_name', 'pack_quantity', 'pack_price', 'unit_type', 'is_active']
        widgets = {
            'drink_name': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Nom de la boisson'
            }),
            'pack_quantity': forms.NumberInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'min': 1,
                'placeholder': 'Nombre par pack'
            }),
            'pack_price': forms.NumberInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Prix du pack'
            }),
            'unit_type': forms.TextInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'placeholder': 'Bouteille, canette...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-purple-500 focus:ring-purple-500'
            }),
        }
        labels = {
            'drink_name': _('Nom de la boisson'),
            'pack_quantity': _('Quantité par pack'),
            'pack_price': _('Prix par pack'),
            'unit_type': _('Type d\'unité'),
            'is_active': _('Actif'),
        }