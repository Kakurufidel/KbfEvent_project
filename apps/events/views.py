import logging
from django.utils import timezone 
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View, FormView
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import EventForm
from apps.guests.forms import RSVPForm
from .models import Event, EventCollaborator
from django.urls import reverse_lazy
from .models import Table
from .forms import TableForm



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
    success_url = reverse_lazy('authentication:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Créer un événement')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        event = form.save(commit=False)
        event.main_organizer = self.request.user
        event.save()
        messages.success(self.request, _('Événement créé avec succès !'))
        return redirect(self.success_url)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{error}")
        return super().form_invalid(form)


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modifier un événement existant"""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('authentication:dashboard')
    
    def test_func(self):
        event = self.get_object()
        return user_can_manage_event(self.request.user, event)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Modifier l\'événement')
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Événement modifié avec succès !'))
        return redirect(self.success_url)


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


class JoinCoOrganizerView(FormView):
    """Vue pour rejoindre comme co-organisateur (basée sur classe)"""
    template_name = 'events/join_coorganizer.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=kwargs.get('slug'), coorganizer_token=kwargs.get('token'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_class(self):
        from apps.authentication.forms import RegisterForm
        return RegisterForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        return context
    
    def form_valid(self, form):
        # Créer l'utilisateur
        user = form.save()
        
        # Connecter l'utilisateur
        login(self.request, user)
        
        # Ajouter comme co-organisateur
        EventCollaborator.objects.create(
            event=self.event,
            user=user,
            status='accepted',
            accepted_at=timezone.now()
        )
        
        messages.success(self.request, f'Bienvenue ! Vous êtes co-organisateur de "{self.event.name}"')
        return redirect('events:event_detail', slug=self.event.slug)
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)
    
    def get(self, request, *args, **kwargs):
        # Si déjà connecté, l'ajouter directement comme co-organisateur
        if request.user.is_authenticated:
            collaborator, created = EventCollaborator.objects.get_or_create(
                event=self.event,
                user=request.user,
                defaults={'status': 'accepted', 'accepted_at': timezone.now()}
            )
            if not created and collaborator.status == 'pending':
                collaborator.status = 'accepted'
                collaborator.accepted_at = timezone.now()
                collaborator.save()
            
            messages.success(request, f'Vous êtes maintenant co-organisateur de "{self.event.name}"')
            return redirect('events:event_detail', slug=self.event.slug)
        
        return super().get(request, *args, **kwargs)

class RSVPFormView(FormView):
    """Formulaire public pour les invités"""
    template_name = 'events/rsvp_form.html'
    form_class = RSVPForm
    success_url = reverse_lazy('events:rsvp_thanks')
    
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(
            Event, 
            slug=kwargs.get('slug'), 
            rsvp_token=kwargs.get('token'),
            is_active=True
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['event'] = self.event
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        return context
    
    def form_valid(self, form):
        response = form.save(commit=False)
        response.event = self.event
        response.ip_address = self.request.META.get('REMOTE_ADDR')
        response.save()
        
        # Vérification si l'invité est dans la liste
        response.verify_against_invited_list()
        
        # Envoi de l'email de confirmation
        try:
            response.send_confirmation_email()
        except Exception as e:
            print(f"Erreur envoi email: {e}")
        
        messages.success(self.request, _('Merci ! Votre réponse a bien été enregistrée.'))
        return super().form_valid(form)

class TableListView(LoginRequiredMixin, ListView):
    model = Table
    template_name = 'events/table_list.html'
    context_object_name = 'tables'

    def get_queryset(self):
        return Table.objects.filter(event_id=self.kwargs['event_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, id=self.kwargs['event_id'], main_organizer=self.request.user)
        return context

class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    form_class = TableForm
    template_name = 'events/table_form.html'

    def form_valid(self, form):
        form.instance.event_id = self.kwargs['event_id']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('events:table_list', kwargs={'event_id': self.kwargs['event_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, id=self.kwargs['event_id'], main_organizer=self.request.user)
        return context
    
class AutoAssignTablesView(LoginRequiredMixin, View):
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        service = TableAssignmentService(event)
        service.auto_assign_all()
        messages.success(request, "Les tables ont été attribuées automatiquement.")
        return redirect('events:event_detail', event_id=event.id)
