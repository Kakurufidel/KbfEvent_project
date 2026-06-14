from django.urls import path
from . import views

app_name = 'guests'

urlpatterns = [
    # RSVP public
    path('rsvp/<uuid:token>/', views.RSVPView.as_view(), name='rsvp'),
    path('invitation/<uuid:token>/', views.InvitationPDFView.as_view(), name='invitation_pdf'),
    
    # Gestion des invités (organisateur)
    path('event/<int:event_id>/', views.GuestListView.as_view(), name='guest_list'),
    path('event/<int:event_id>/import/', views.BulkImportGuestsView.as_view(), name='bulk_import'),
    
    # Exports
    path('export/csv/<int:event_id>/', views.ExportGuestsCSVView.as_view(), name='export_csv'),
    path('export/excel/<int:event_id>/', views.ExportGuestsExcelView.as_view(), name='export_excel'),
]