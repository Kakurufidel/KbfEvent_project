import csv
import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, TemplateView, FormView, CreateView, DetailView, ListView, UpdateView, View, FormView, DeleteView
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _


from apps.events.models import Event
from .models import GuestResponse, InvitedGuest
from .forms import RSVPForm, InvitedGuestForm, GuestBulkImportForm
from .services import import_guests_from_excel, generate_invitation_pdf

logger = logging.getLogger(__name__)


class GuestListView(LoginRequiredMixin, ListView):
    template_name = 'guests/guest_list.html'
    context_object_name = 'guests'

    def get_paginate_by(self, queryset):
        # 1. Essayer de lire depuis les paramètres GET
        per_page = self.request.GET.get('per_page')
        if per_page and per_page.isdigit():
            per_page = int(per_page)
            # Limiter les valeurs possibles pour éviter des abus
            if per_page in [10, 15, 20, 30, 50, 100]:
                return per_page
        # 2. Sinon, utiliser la valeur par défaut depuis settings
        return getattr(settings, 'GUESTS_PER_PAGE', 20)

    def get_queryset(self):
        self.event = get_object_or_404(
            Event,
            id=self.kwargs.get('event_id'),
            main_organizer=self.request.user
        )
        return self.event.responses.all().order_by('-submitted_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['current_per_page'] = self.get_paginate_by(self.get_queryset())
        # Statistiques (inchangées)
        responses = self.event.responses
        context['stats'] = {
            'total': responses.count(),
            'attending': responses.filter(will_attend=True).count(),
            'not_attending': responses.filter(will_attend=False).count(),
            'verified': responses.filter(verification_status='verified').count(),
            'unverified': responses.filter(verification_status='unverified').count(),
        }
        return context


class ExportGuestsCSVView(LoginRequiredMixin, View):
    """Export CSV des réponses invités"""
    
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        responses = event.responses.all().order_by('-submitted_at')
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="responses_{event.id}.csv"'
        response.write('\ufeff')
        
        writer = csv.writer(response)
        writer.writerow([
            _('First name'), _('Last name'), _('Email'), _('Phone'),
            _('Will attend'), _('Number of guests'), _('Accompanied'),
            _('Drink choice'), _('Other drink'), _('Verification status'),
            _('Submitted at')
        ])
        
        for r in responses:
            writer.writerow([
                r.first_name, r.last_name, r.email, r.phone,
                _('Yes') if r.will_attend else _('No'),
                r.number_of_guests,
                _('Yes') if r.is_accompanied else _('No'),
                r.drink_display, r.drink_other or '',
                r.get_verification_status_display(),
                r.submitted_at.strftime('%d/%m/%Y %H:%M'),
            ])
        
        return response


class ExportGuestsExcelView(LoginRequiredMixin, View):
    """Export Excel des réponses invités"""
    
    def get(self, request, event_id):
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        responses = event.responses.all().order_by('-submitted_at')
        
        wb = Workbook()
        ws = wb.active
        ws.title = str(_('Responses'))
        
        headers = [
            _('First name'), _('Last name'), _('Email'), _('Phone'),
            _('Will attend'), _('Number of guests'), _('Accompanied'),
            _('Drink choice'), _('Other drink'), _('Verification status'),
            _('Submitted at')
        ]
        
        header_font = Font(bold=True)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        for row, r in enumerate(responses, 2):
            ws.cell(row=row, column=1, value=r.first_name)
            ws.cell(row=row, column=2, value=r.last_name)
            ws.cell(row=row, column=3, value=r.email)
            ws.cell(row=row, column=4, value=r.phone)
            ws.cell(row=row, column=5, value=_('Yes') if r.will_attend else _('No'))
            ws.cell(row=row, column=6, value=r.number_of_guests)
            ws.cell(row=row, column=7, value=_('Yes') if r.is_accompanied else _('No'))
            ws.cell(row=row, column=8, value=r.drink_display)
            ws.cell(row=row, column=9, value=r.drink_other or '')
            ws.cell(row=row, column=10, value=r.get_verification_status_display())
            ws.cell(row=row, column=11, value=r.submitted_at.strftime('%d/%m/%Y %H:%M'))
        
        # Ajuster les colonnes
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="responses_{event.id}.xlsx"'
        wb.save(response)
        return response


class RSVPThanksView(TemplateView):
    """Page de remerciement après RSVP"""
    template_name = 'guests/rsvp_thanks.html'


class BulkImportGuestsView(LoginRequiredMixin, View):
    """Import Excel d'invités pré-enregistrés"""
    template_name = 'guests/bulk_import.html'

    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        form = GuestBulkImportForm()
        return render(request, self.template_name, {
            'form': form,
            'event': event
        })

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        form = GuestBulkImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            result = import_guests_from_excel(excel_file, event, request.user)
            
            messages.success(
                request, 
                _('Import terminé: %(created)s invités ajoutés, %(errors)s erreurs') % {
                    'created': result['created'],
                    'errors': result['errors']
                }
            )
            return redirect('guests:guest_list', event_id=event.id)
        
        return render(request, self.template_name, {
            'form': form,
            'event': event
        })


# ========== CHECK-IN ==========
class CheckInView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Vue pour scanner le QR code (ou saisir le code court) et valider l'arrivée d'un invité.
    Accessible uniquement aux organisateurs et co-organisateurs avec can_scan=True.
    """
    template_name = 'guests/checkin.html'
    success_template = 'guests/checkin_success.html'

    def test_func(self):
        # Vérification des droits : on le fait dans dispatch pour avoir accès à l'événement
        return True  # On le fait manuellement dans dispatch

    def dispatch(self, request, *args, **kwargs):
        token = kwargs.get('token')
        # Tentative de trouver la GuestResponse via le token (UUID ou short_code)
        try:
            import uuid
            uuid_obj = uuid.UUID(token)
            self.guest_response = get_object_or_404(GuestResponse, invitation_token=uuid_obj)
        except ValueError:
            self.guest_response = get_object_or_404(GuestResponse, short_code=token)

        # Vérification des droits
        user = request.user
        event = self.guest_response.event
        is_organizer = (event.main_organizer == user)
        is_collaborator_with_scan = event.collaborators.filter(user=user, can_scan=True).exists()

        if not (is_organizer or is_collaborator_with_scan):
            messages.error(request, _("Vous n'avez pas l'autorisation de scanner les invitations pour cet événement."))
            return redirect('events:event_list')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        guest = self.guest_response
        if guest.checkin_time:
            return render(request, self.template_name, {
                'guest': guest,
                'already_checked_in': True,
                'message': _("Cette invitation a déjà été scannée à {}.").format(guest.checkin_time.strftime("%H:%M:%S"))
            })
        # Afficher le formulaire de confirmation
        return render(request, self.template_name, {
            'guest': guest,
            'already_checked_in': False,
        })

    def post(self, request, *args, **kwargs):
        guest = self.guest_response
        if guest.checkin_time:
            messages.warning(request, _("Cette invitation a déjà été utilisée."))
            return redirect('guests:checkin', token=kwargs.get('token'))

        # Enregistrer le check-in
        guest.checkin_time = timezone.now()
        guest.save(update_fields=['checkin_time'])

        table_number = guest.table.number if guest.table else _("non assignée")

        messages.success(request, _("Bienvenue {} ! Vous êtes à la table {}.").format(guest.get_full_name(), table_number))

        return render(request, self.success_template, {
            'guest': guest,
            'table_number': table_number,
        })


# ========== INVITATION PDF ==========
class InvitationPDFView(View):
    """Génère l'invitation électronique en PDF"""
    
    def get(self, request, token):
        guest_response = get_object_or_404(GuestResponse, invitation_token=token)
        pdf = generate_invitation_pdf(guest_response)
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invitation_{guest_response.event.slug}.pdf"'
        return response
    

class AddInvitedGuestView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = InvitedGuest
    form_class = InvitedGuestForm
    template_name = 'guests/add_guest.html'  # Assurez-vous que ce template existe

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs['event_id'])
        return self.request.user == self.event.main_organizer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        return context

    def form_valid(self, form):
        form.instance.event = self.event
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Invité ajouté avec succès.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('guests:invited_list', kwargs={'event_id': self.event.id})
# ========== INVITÉS PRÉ-ENREGISTRÉS ==========

class InvitedGuestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Liste des invités pré-enregistrés (InvitedGuest) pour un événement.
    Accessible uniquement à l'organisateur principal.
    """
    model = InvitedGuest
    template_name = 'guests/invited_guest_list.html'
    context_object_name = 'invited_guests'
    paginate_by = 20

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs['event_id'])
        return self.request.user == self.event.main_organizer

    def get_queryset(self):
        return InvitedGuest.objects.filter(event=self.event).order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['total'] = self.get_queryset().count()
        return context


class ExportInvitedCSVView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Export CSV de la liste des invités pré-enregistrés.
    """
    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs['event_id'])
        return self.request.user == self.event.main_organizer

    def get(self, request, event_id):
        guests = InvitedGuest.objects.filter(event=self.event).order_by('last_name', 'first_name')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="invited_guests_{self.event.id}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Prénom', 'Nom', 'Postnom', 'Email', 'Téléphone', 'Table'])
        for g in guests:
            writer.writerow([
                g.first_name,
                g.last_name,
                g.middle_name or '',
                g.email or '',
                g.phone or '',
                g.table.number if g.table else ''
            ])
        return response


class ExportInvitedExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Export Excel de la liste des invités pré-enregistrés.
    """
    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs['event_id'])
        return self.request.user == self.event.main_organizer

    def get(self, request, event_id):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        guests = InvitedGuest.objects.filter(event=self.event).order_by('last_name', 'first_name')
        wb = Workbook()
        ws = wb.active
        ws.title = "Invités"
        headers = ['Prénom', 'Nom', 'Postnom', 'Email', 'Téléphone', 'Table']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
        for row, g in enumerate(guests, 2):
            ws.cell(row=row, column=1, value=g.first_name)
            ws.cell(row=row, column=2, value=g.last_name)
            ws.cell(row=row, column=3, value=g.middle_name or '')
            ws.cell(row=row, column=4, value=g.email or '')
            ws.cell(row=row, column=5, value=g.phone or '')
            ws.cell(row=row, column=6, value=g.table.number if g.table else '')
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="invited_guests_{self.event.id}.xlsx"'
        wb.save(response)
        return response