import csv
import io
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView
from .models import Guest
from apps.events.models import Event
from .forms import RSVPForm, InvitedGuestForm


class RSVPView(View):
    """Vue publique pour répondre à une invitation """
    template_name = 'guests/rsvp.html'
    thanks_template = 'guests/rsvp_thanks.html'
    already_template = 'guests/rsvp_already.html'

    def get(self, request, *args, **kwargs):
        guest = get_object_or_404(Guest, unique_token=kwargs.get('token'))
        if guest.status != 'pending':
            return render(request, self.already_template, {'guest': guest})
        form = RSVPForm(event=guest.event)
        return render(request, self.template_name, {
            'form': form,
            'guest': guest,
            'event': guest.event,
        })

    def post(self, request, *args, **kwargs):
        guest = get_object_or_404(Guest, unique_token=kwargs.get('token'))
        if guest.status != 'pending':
            return render(request, self.already_template, {'guest': guest})
        form = RSVPForm(request.POST, event=guest.event)
        if form.is_valid():
            cd = form.cleaned_data
            guest.status = cd['status']
            if cd['status'] == 'confirmed':
                guest.drink_choice = cd['drink_choice'] if cd['drink_choice'] != 'other' else ''
                guest.drink_other = cd['drink_other'] if cd['drink_choice'] == 'other' else ''
                guest.is_accompanied = cd['is_accompanied']
                if cd['is_accompanied']:
                    guest.companion_drink_choice = cd['companion_drink_choice'] if cd['companion_drink_choice'] != 'other' else ''
                    guest.companion_drink_other = cd['companion_drink_other'] if cd['companion_drink_choice'] == 'other' else ''
            else:
                guest.status = 'declined'
            guest.save()
            return render(request, self.thanks_template, {'guest': guest, 'status': cd['status']})
        return render(request, self.template_name, {
            'form': form,
            'guest': guest,
            'event': guest.event,
        })


class GuestListView(LoginRequiredMixin, TemplateView):
    template_name = 'guests/guest_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, id=kwargs.get('event_id'), main_organizer=self.request.user)
        guests = event.guests.all().order_by('-created_at')  # Note: guests est l'ancienne relation

        status_filter = self.request.GET.get('status', '')
        search_query = self.request.GET.get('q', '')

        if status_filter:
            guests = guests.filter(status=status_filter)
        if search_query:
            guests = guests.filter(
                first_name__icontains=search_query
            ) | guests.filter(
                last_name__icontains=search_query
            ) | guests.filter(
                email__icontains=search_query
            )

        context['event'] = event
        context['guests'] = guests
        context['status_filter'] = status_filter
        context['search_query'] = search_query
        return context


class ExportGuestsCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        event = get_object_or_404(Event, id=kwargs.get('event_id'), main_organizer=request.user)
        guests = event.guests.all().order_by('-created_at')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="guests_{event.id}.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            _('First name'), _('Last name'), _('Email'), _('Phone'),
            _('Status'), _('Drink'), _('Other drink'),
            _('Accompanied'), _('Companion drink'), _('Companion other drink'),
            _('RSVP link'),
        ])
        for guest in guests:
            writer.writerow([
                guest.first_name, guest.last_name, guest.email, guest.phone,
                guest.get_status_display(),
                guest.drink_choice or '', guest.drink_other or '',
                _('Yes') if guest.is_accompanied else _('No'),
                guest.companion_drink_choice or '', guest.companion_drink_other or '',
                request.build_absolute_uri(guest.get_rsvp_link()),
            ])
        return response


class ExportGuestsExcelView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        event = get_object_or_404(Event, id=kwargs.get('event_id'), main_organizer=request.user)
        guests = event.guests.all().order_by('-created_at')

        wb = Workbook()
        ws = wb.active
        ws.title = str(_('Guests'))

        headers = [
            _('First name'), _('Last name'), _('Email'), _('Phone'),
            _('Status'), _('Drink'), _('Other drink'),
            _('Accompanied'), _('Companion drink'), _('Companion other drink'),
            _('RSVP link'),
        ]
        header_font = Font(bold=True)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font

        for row, guest in enumerate(guests, 2):
            ws.cell(row=row, column=1, value=guest.first_name)
            ws.cell(row=row, column=2, value=guest.last_name)
            ws.cell(row=row, column=3, value=guest.email)
            ws.cell(row=row, column=4, value=guest.phone)
            ws.cell(row=row, column=5, value=guest.get_status_display())
            ws.cell(row=row, column=6, value=guest.drink_choice or '')
            ws.cell(row=row, column=7, value=guest.drink_other or '')
            ws.cell(row=row, column=8, value=_('Yes') if guest.is_accompanied else _('No'))
            ws.cell(row=row, column=9, value=guest.companion_drink_choice or '')
            ws.cell(row=row, column=10, value=guest.companion_drink_other or '')
            ws.cell(row=row, column=11, value=request.build_absolute_uri(guest.get_rsvp_link()))

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="guests_{event.id}.xlsx"'
        wb.save(response)
        return response