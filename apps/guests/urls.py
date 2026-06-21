from django.urls import path
from . import views

app_name = 'guests'

urlpatterns = [
    # RSVP public (lien unique pour tous les invités – géré dans events/urls.py)
    # path('rsvp/<uuid:token>/', views.RSVPView.as_view(), name='rsvp'),  # SUPPRIMÉ

    # Page de remerciement
    path('thanks/', views.RSVPThanksView.as_view(), name='rsvp_thanks'),

    # Gestion des invités (organisateur)
    path('event/<int:event_id>/', views.GuestListView.as_view(), name='guest_list'),
    path('event/<int:event_id>/import/', views.BulkImportGuestsView.as_view(), name='bulk_import'),
    path('checkin/<str:token>/', views.CheckInView.as_view(), name='checkin'),

    # Exports
    path('export/csv/<int:event_id>/', views.ExportGuestsCSVView.as_view(), name='export_csv'),
    path('export/excel/<int:event_id>/', views.ExportGuestsExcelView.as_view(), name='export_excel'),

    # PDF invitation (si nécessaire)
    path('invitation/<uuid:token>/', views.InvitationPDFView.as_view(), name='invitation_pdf'),
    path('event/<int:event_id>/invited/', views.InvitedGuestListView.as_view(), name='invited_list'),
    path('event/<int:event_id>/export-invited-csv/', views.ExportInvitedCSVView.as_view(), name='export_invited_csv'),
    path('event/<int:event_id>/export-invited-excel/', views.ExportInvitedExcelView.as_view(), name='export_invited_excel'),

]