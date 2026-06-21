from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, TemplateView
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import LoginForm, RegisterForm
from apps.events.models import Event


class HomeView(TemplateView):
    """Page d'accueil - redirige vers le dashboard si connecté"""
    template_name = 'landing.html'  
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:event_list')
        return super().get(request, *args, **kwargs)


def redirect_after_auth(request, user):
    """
    Fonction utilitaire pour rediriger après authentification.
    Si un code co-organisateur est fourni, redirige vers l'événement correspondant.
    """
    coorganizer_code = request.POST.get('coorganizer_code')
    if coorganizer_code:
        try:
            event = Event.objects.get(coorganizer_short_code=coorganizer_code.upper())
            # CORRECTION : utilisation du slug au lieu de event_id
            return redirect('events:event_detail', slug=event.slug)
        except Event.DoesNotExist:
            messages.warning(request, _('Le code co-organisateur est invalide.'))
    # Sinon, rediriger vers la liste des événements
    return redirect('events:event_list')


class LoginView(FormView):
    template_name = 'authentication/login.html'
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:event_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        coorganizer_code = self.request.GET.get('coorganizer_code')
        if coorganizer_code:
            initial['coorganizer_code'] = coorganizer_code
        return initial

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, _('Bon retour parmis nous, %(name)s !') % {'name': user.first_name})
        return redirect_after_auth(self.request, user)

    def form_invalid(self, form):
        messages.error(self.request, _('Email ou mot de passe incorrect.'))
        return super().form_invalid(form)


class RegisterView(FormView):
    template_name = 'authentication/register.html'
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:event_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        coorganizer_code = self.request.GET.get('coorganizer_code')
        if coorganizer_code:
            initial['coorganizer_code'] = coorganizer_code
        return initial

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, _('Bienvenue ! Votre compte a été créé avec succès.'))
        return redirect_after_auth(self.request, user)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)


class LogoutView(View):
    """Vue de déconnexion"""

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, _('Vous avez été déconnecté avec succès.'))
        return redirect(reverse('authentication:home'))


class ContactView(View):
    """Vue pour traiter le formulaire de contact"""

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect(reverse('authentication:home') + '#contact')

        messages.success(
            request,
            f"Merci {name} ! Votre message a bien été envoyé. Nous vous répondrons dans les plus brefs délais."
        )

        return redirect(reverse('authentication:home') + '#contact')

    def get(self, request, *args, **kwargs):
        return redirect('authentication:home')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'authentication/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.events.models import Event, EventCollaborator

        # Événements dont l'utilisateur est l'organisateur principal
        events = Event.objects.filter(main_organizer=self.request.user)
        is_organizer = events.exists()  # True si au moins un événement où il est main_organizer

        # Co-organisateurs (pour tous les événements dont il est main_organizer)
        collaborators = EventCollaborator.objects.filter(
            event__main_organizer=self.request.user,
            status='accepted'
        ).select_related('user')

        context.update({
            'events': events,
            'total_events': events.count(),
            'collaborators': collaborators,
            'total_guests': 0,      # À calculer si besoin
            'total_responses': 0,
            'attendance_rate': 0,
            'is_organizer': is_organizer,  # NOUVEAU
        })
        return context