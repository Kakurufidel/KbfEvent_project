from django.views.generic import CreateView, ListView, UpdateView, TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from apps.events.models import Event
from .models import PaymentRequest
from .forms import PaymentRequestForm, AdminPaymentApprovalForm


class PaymentRequestCreateView(LoginRequiredMixin, CreateView):
    model = PaymentRequest
    form_class = PaymentRequestForm
    template_name = 'payments/request_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, id=self.kwargs.get('event_id'))
        # Vérifier que l'utilisateur est l'organisateur principal
        if self.event.main_organizer != request.user:
            messages.error(request, _("Vous n'avez pas le droit de faire une demande de paiement pour cet événement."))
            return redirect('events:event_detail', slug=self.event.slug)
        # Vérifier que le paiement n'a pas déjà été approuvé
        if self.event.is_paid:
            messages.warning(request, _("Cet événement est déjà payé."))
            return redirect('events:event_detail', slug=self.event.slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['title'] = _('Demande de paiement')
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.event = self.event
        response = super().form_valid(form)
        # Envoyer une notification à l'admin
        self.send_admin_notification(form.instance)
        messages.success(
            self.request,
            _('Votre demande de paiement a été envoyée. Un administrateur la validera dans les plus brefs délais.')
        )
        return response

    def send_admin_notification(self, payment_request):
        """Envoie un email à l'admin pour notifier une nouvelle demande"""
        try:
            # Récupérer l'email de l'admin (à configurer dans settings)
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')

            context = {
                'payment': payment_request,
                'event': payment_request.event,
                'user': payment_request.user,
                'admin_url': self.request.build_absolute_uri(
                    reverse_lazy('payments:admin_list')
                ),
            }

            html_message = render_to_string('payments/emails/admin_notification.html', context)
            plain_message = render_to_string('payments/emails/admin_notification.txt', context)

            send_mail(
                subject=f'[KbfEven] Nouvelle demande de paiement - {payment_request.event.name}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur envoi email admin: {e}")

    def get_success_url(self):
        return reverse_lazy('events:event_detail', kwargs={'slug': self.event.slug})


class AdminPaymentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = PaymentRequest
    template_name = 'payments/admin_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = PaymentRequest.objects.all().order_by('-created_at')
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['counts'] = {
            'pending': PaymentRequest.objects.filter(status='pending').count(),
            'approved': PaymentRequest.objects.filter(status='approved').count(),
            'rejected': PaymentRequest.objects.filter(status='rejected').count(),
        }
        return context


class AdminPaymentApproveView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = PaymentRequest
    template_name = 'payments/admin_approve.html'
    form_class = AdminPaymentApprovalForm
    context_object_name = 'payment'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Approuver/Rejeter - {self.object.event.name}"
        return context

    def form_valid(self, form):
        payment = self.object
        status = form.cleaned_data['status']
        admin_notes = form.cleaned_data['admin_notes']

        payment.status = status
        payment.admin_notes = admin_notes
        if status == 'approved':
            payment.approved_at = timezone.now()
            # Débloquer l'événement
            payment.event.is_paid = True
            payment.event.save()

        payment.save()

        messages.success(self.request, f"La demande a été {status}.")

        # Notifier l'utilisateur
        self.send_user_notification(payment)

        return redirect('payments:admin_list')

    def send_user_notification(self, payment):
        """Envoie un email à l'utilisateur pour l'informer du statut de sa demande"""
        try:
            context = {
                'payment': payment,
                'event': payment.event,
            }

            if payment.status == 'approved':
                template_html = 'payments/emails/user_approved.html'
                template_txt = 'payments/emails/user_approved.txt'
                subject = f'[KbfEven] Votre demande de paiement a été approuvée'
            else:
                template_html = 'payments/emails/user_rejected.html'
                template_txt = 'payments/emails/user_rejected.txt'
                subject = f'[KbfEven] Votre demande de paiement a été rejetée'

            html_message = render_to_string(template_html, context)
            plain_message = render_to_string(template_txt, context)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[payment.user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur envoi email utilisateur: {e}")