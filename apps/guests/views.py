# apps/guests/views.py
import csv
import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.urls import reverse

from apps.events.models import Event
from .models import GuestResponse, InvitedGuest
from .forms import RSVPForm, InvitedGuestForm, GuestBulkImportForm
from .services import import_guests_from_excel, generate_invitation_pdf

logger = logging.getLogger(__name__)


class RSVPView(View):
    """Vue publique pour répondre à une invitation (lien unique)"""
    
    template_name = 'guests/rsvp.html'
    thanks_template = 'guests/rsvp_thanks.html'
    already_template = 'guests/rsvp_already.html'

    def get(self, request, token):
        guest = get_object_or_404(GuestResponse, invitation_token=token)
        
        if guest.will_attend is not None and guest.submitted_at:
            # Déjà répondu
            return render(request, self.already_template, {
                'guest': guest,
                'event': guest.event
            })
        
        form = RSVPForm(event=guest.event, instance=guest)
        return render(request, self.template_name, {
            'form': form,
            'guest': guest,
            'event': guest.event,
        })

    def post(self, request, token):
        guest = get_object_or_404(GuestResponse, invitation_token=token)
        
        if guest.will_attend is not None and guest.submitted_at:
            return render(request, self.already_template, {
                'guest': guest,
                'event': guest.event
            })
        
        form = RSVPForm(request.POST, event=guest.event, instance=guest)
        
        if form.is_valid():
            response = form.save(commit=False)
            response.ip_address = request.META.get('REMOTE_ADDR')
            response.save()
            
            if response.will_attend:
                messages.success(request, _('Merci ! Votre présence a été confirmée. Vous allez recevoir un email avec tous les détails.'))
            else:
                messages.info(request, _('Nous sommes désolés que vous ne puissiez pas venir. Merci de nous avoir prévenus.'))
            
            return render(request, self.thanks_template, {
                'guest': response,
                'will_attend': response.will_attend,
                'event': guest.event
            })
        
        return render(request, self.template_name, {
            'form': form,
            'guest': guest,
            'event': guest.event,
        })


class GuestListView(LoginRequiredMixin, ListView):
    """Liste des invités pour un événement"""
    template_name = 'guests/guest_list.html'
    context_object_name = 'guests'
    paginate_by = 50

    def get_queryset(self):
        self.event = get_object_or_404(
            Event, 
            id=self.kwargs.get('event_id'), 
            main_organizer=self.request.user
        )
        queryset = self.event.responses.all().order_by('-submitted_at')
        
        # Filtres
        status_filter = self.request.GET.get('status', '')
        verification_filter = self.request.GET.get('verification', '')
        search_query = self.request.GET.get('q', '')
        
        if status_filter == 'attending':
            queryset = queryset.filter(will_attend=True)
        elif status_filter == 'not_attending':
            queryset = queryset.filter(will_attend=False)
        
        if verification_filter:
            queryset = queryset.filter(verification_status=verification_filter)
        
        if search_query:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['status_filter'] = self.request.GET.get('status', '')
        context['verification_filter'] = self.request.GET.get('verification', '')
        context['search_query'] = self.request.GET.get('q', '')
        
        # Statistiques
        responses = self.event.responses
        context['stats'] = {
            'total': responses.count(),
            'attending': responses.filter(will_attend=True).count(),
            'not_attending': responses.filter(will_attend=False).count(),
            'verified': responses.filter(verification_status='verified').count(),
            'unverified': responses.filter(verification_status='unverified').count(),
            'pending': self.event.invited_guests.count() - responses.filter(verification_status='verified').count(),
        }
        
        return context


class ExportGuestsCSVView(LoginRequiredMixin, View):
    """Export CSV des réponses invités"""
    
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, main_organizer=request.user)
        responses = event.responses.all().order_by('-submitted_at')
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="responses_{event.id}.csv"'
        response.write('\ufeff')  # BOM pour UTF-8
        
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


class InvitationPDFView(View):
    def get(self, request, token):
        guest_response = get_object_or_404(GuestResponse, invitation_token=token)
        pdf = generate_invitation_pdf(guest_response)
        if pdf is None:
            messages.error(request, _("Le PDF n'a pas pu être généré (bibliothèque manquante)."))
            return redirect('guests:rsvp', token=token)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invitation_{guest_response.event.slug}.pdf"'
        return response