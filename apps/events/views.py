import logging
from django.utils import timezone 
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import EventForm
from .models import Event, EventCollaborator


logger = logging.getLogger(__name__)


def user_can_manage_event(user, event):
    """Vérifie si l'utilisateur peut gérer l'événement"""
    return (event.main_organizer == user or 
            EventCollaborator.objects.filter(event=event, user=user, status='accepted').exists())


class EventListView(LoginRequiredMixin, ListView):
    """Liste des événements de l'organisateur"""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        return Event.objects.filter(main_organizer=self.request.user)


class EventCreateView(LoginRequiredMixin, CreateView):
    """Créer un nouvel événement"""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Créer un événement')
        return context

    def form_valid(self, form):
        event = form.save(commit=False)
        event.main_organizer = self.request.user
        event.save()
        messages.success(self.request, _('Événement créé avec succès !'))
        return redirect('events:event_list')


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modifier un événement existant"""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    slug_url_kwarg = 'slug'
    
    def test_func(self):
        event = self.get_object()
        return user_can_manage_event(self.request.user, event)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Modifier l\'événement')
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Événement modifié avec succès !'))
        return redirect('events:event_list')


class EventDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Détail d'un événement avec statistiques"""
    model = Event
    template_name = 'events/event_detail.html'
    slug_url_kwarg = 'slug'
    context_object_name = 'event'

    def test_func(self):
        event = self.get_object()
        return user_can_manage_event(self.request.user, event)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        
        context['invited_guests'] = event.invited_guests.all()[:10]
        context['recent_responses'] = event.responses.all()[:10]
        context['collaborators'] = event.collaborators.filter(status='accepted')
        context['rsvp_url'] = event.get_rsvp_url()
        context['coorganizer_url'] = event.get_coorganizer_url()
        context['stats'] = {
            'total_invited': event.total_invited_guests(),
            'total_responses': event.total_responses(),
            'verified': event.verified_responses(),
            'unverified': event.unverified_responses(),
            'attendance_rate': event.attendance_rate(),
            'will_attend': event.will_attend_count(),
            'expected_guests': event.total_expected_guests(),
        }
        return context


class EventDeleteView(LoginRequiredMixin, View):
    """Supprimer un événement"""
    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=kwargs.get('slug'), main_organizer=request.user)
        name = event.name
        event.delete()
        messages.success(request, _('L\'événement "%(name)s" a été supprimé.') % {'name': name})
        return redirect('events:event_list')
    

class JoinCoOrganizerView(View):
    """Vue pour rejoindre comme co-organisateur"""
    
    def get(self, request, slug, token):
        event = get_object_or_404(Event, slug=slug, coorganizer_token=token)
        
        if request.user.is_authenticated:
            # Déjà connecté
            collaborator, created = EventCollaborator.objects.get_or_create(
                event=event,
                user=request.user,
                defaults={'status': 'accepted', 'accepted_at': timezone.now()}
            )
            if not created and collaborator.status == 'pending':
                collaborator.status = 'accepted'
                collaborator.accepted_at = timezone.now()
                collaborator.save()
            
            messages.success(request, f'Vous êtes maintenant co-organisateur de "{event.name}"')
            return redirect('events:event_detail', slug=event.slug)
        
        # Formulaire d'inscription
        from apps.authentication.forms import RegisterForm
        form = RegisterForm()
        return render(request, 'events/join_coorganizer.html', {
            'form': form,
            'event': event,
        })
    
    def post(self, request, slug, token):
        event = get_object_or_404(Event, slug=slug, coorganizer_token=token)
        from apps.authentication.forms import RegisterForm
        
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            EventCollaborator.objects.create(
                event=event,
                user=user,
                status='accepted',
                accepted_at=timezone.now()
            )
            
            messages.success(request, f'Bienvenue ! Vous êtes co-organisateur de "{event.name}"')
            return redirect('events:event_detail', slug=event.slug)
        
        return render(request, 'events/join_coorganizer.html', {
            'form': form,
            'event': event,
        })