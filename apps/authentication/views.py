from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, TemplateView
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import LoginForm, RegisterForm


class HomeView(TemplateView):
    """Page d'accueil - redirige vers le dashboard si connecté"""
    template_name = 'authentication/landing.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:event_list')
        return super().get(request, *args, **kwargs)


class LoginView(FormView):
    template_name = 'authentication/login.html'
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:event_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, _('Bon retour parmis nous, %(name)s !') % {'name': user.first_name})
        return redirect('events:event_list')

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

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, _('Bienvenue ! Votre compte a été créé avec succès.'))
        return redirect('events:event_list')

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
    """Tableau de bord de l'utilisateur"""
    template_name = 'authentication/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.events.models import Event, EventCollaborator
        
        print("=" * 50)
        print(f"DEBUG DashboardView - Utilisateur: {self.request.user.email}")
        
        # Evenements dont l'utilisateur est l'organisateur principal
        events = Event.objects.filter(main_organizer=self.request.user)
        print(f"Nombre d'evenements trouves: {events.count()}")
        
        for e in events:
            print(f"  - {e.name}")
        print("=" * 50)
        
        # Co-organisateurs
        collaborators = EventCollaborator.objects.filter(
            event__main_organizer=self.request.user,
            status='accepted'
        ).select_related('user')
        
        context.update({
            'events': events,
            'total_events': events.count(),
            'collaborators': collaborators,
            'total_guests': 0,
            'total_responses': 0,
            'attendance_rate': 0,
        })
        
        return context