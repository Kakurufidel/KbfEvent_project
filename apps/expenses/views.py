import json
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from datetime import datetime

from apps.events.models import Event
from .models import BeveragePack
from .forms import BeveragePackForm
from .services import EstimationService


class BeveragePackListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = BeveragePack
    template_name = 'expenses/beveragepack_list.html'
    context_object_name = 'packs'

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs.get('event_id'))
        user = self.request.user
        return (self.event.main_organizer == user or
                self.event.collaborators.filter(user=user, status='accepted').exists())

    def get_queryset(self):
        return BeveragePack.objects.filter(event=self.event).order_by('drink_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        return context


class BeveragePackCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = BeveragePack
    form_class = BeveragePackForm
    template_name = 'expenses/beveragepack_form.html'

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs['event_id'])
        return self.event.main_organizer == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['title'] = _('Ajouter un pack de boisson')
        return context

    def form_valid(self, form):
        form.instance.event = self.event
        messages.success(self.request, _('Pack ajouté avec succès.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('expenses:beveragepack_list', kwargs={'event_id': self.event.id})


class BeveragePackUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BeveragePack
    form_class = BeveragePackForm
    template_name = 'expenses/beveragepack_form.html'

    def test_func(self):
        pack = self.get_object()
        return pack.event.main_organizer == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object.event
        context['title'] = _('Modifier le pack')
        return context

    def form_valid(self, form):
        messages.success(self.request, _('Pack modifié avec succès.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('expenses:beveragepack_list', kwargs={'event_id': self.object.event.id})


class BeveragePackDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = BeveragePack
    template_name = 'expenses/beveragepack_confirm_delete.html'

    def test_func(self):
        pack = self.get_object()
        return pack.event.main_organizer == self.request.user

    def get_success_url(self):
        return reverse_lazy('expenses:beveragepack_list', kwargs={'event_id': self.object.event.id})


class EstimationDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'expenses/estimation.html'

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs.get('event_id'))
        user = self.request.user
        return (self.event.main_organizer == user or
                self.event.collaborators.filter(user=user, status='accepted').exists())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.event

        # Service d'estimation
        service = EstimationService(event, include_pending=True, attendance_rate=0.75)

        # Données d'estimation
        estimation = service.calculate_needs()

        # Données pour le graphique
        chart_data = service.get_chart_data()

        context.update({
            'event': event,
            'estimation': estimation,
            'chart_data': json.dumps(chart_data),
            'has_packs': BeveragePack.objects.filter(event=event, is_active=True).exists(),
        })
        return context


class ExportDevisPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Exporte un PDF contenant le devis des dépenses
    """

    def test_func(self):
        self.event = get_object_or_404(Event, id=self.kwargs.get('event_id'))
        return self.event.main_organizer == self.request.user

    def get(self, request, event_id):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO

        event = self.event
        service = EstimationService(event)
        estimation = service.calculate_needs()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)

        styles = getSampleStyleSheet()

        # Style personnalisé pour le titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=30
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=1,
            spaceAfter=20
        )

        story = []

        # En-tête
        story.append(Paragraph("Devis - Estimation des dépenses", title_style))
        story.append(Paragraph(f"Événement: {event.name}", subtitle_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
        story.append(Spacer(1, 20))

        # Tableau des coûts
        data = [
            ['Boisson', 'Unités nécessaires', 'Packs nécessaires', 'Coût'],
        ]

        for item in estimation['details']:
            data.append([
                item['drink_name'],
                str(item['needed_units']),
                str(item['packs_needed']),
                f"{item['cost']:.2f} €"
            ])

        # Total
        data.append(['', '', 'Total', f"{estimation['total_cost']:.2f} €"])

        table = Table(data, colWidths=[100, 80, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B5CF6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(table)
        story.append(Spacer(1, 20))

        # Résumé
        summary = [
            f"Total des unités nécessaires: {estimation['total_units']}",
            f"Total des packs nécessaires: {estimation['total_packs']}",
            f"Coût total estimé: {estimation['total_cost']:.2f} €",
        ]

        for line in summary:
            story.append(Paragraph(line, styles['Normal']))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="devis_{event.slug}.pdf"'
        return response
    
