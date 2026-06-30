from django import forms
from django.utils.translation import gettext_lazy as _
from .models import PaymentRequest


class PaymentRequestForm(forms.ModelForm):
    """Formulaire pour faire une demande de paiement"""

    class Meta:
        model = PaymentRequest
        fields = ['plan', 'screenshot']
        widgets = {
            'plan': forms.Select(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400'
            }),
            'screenshot': forms.FileInput(attrs={
                'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400',
                'accept': 'image/*'
            }),
        }
        labels = {
            'plan': _('Plan'),
            'screenshot': _('Capture d\'écran du paiement'),
        }
        help_texts = {
            'screenshot': _('Téléchargez une capture d\'écran de votre paiement (PNG, JPG).'),
        }


class AdminPaymentApprovalForm(forms.Form):
    """Formulaire admin pour approuver/rejeter"""
    status = forms.ChoiceField(
        choices=PaymentRequest.Status.choices,
        widget=forms.Select(attrs={'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400'})
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:outline-none focus:border-purple-400'})
    )