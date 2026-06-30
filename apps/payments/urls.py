from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Utilisateur
    path('event/<int:event_id>/request/', views.PaymentRequestCreateView.as_view(), name='request'),

    # Admin
    path('admin/list/', views.AdminPaymentListView.as_view(), name='admin_list'),
    path('admin/<int:pk>/approve/', views.AdminPaymentApproveView.as_view(), name='admin_approve'),
]