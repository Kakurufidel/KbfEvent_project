from django.urls import path
from . import views

app_name = 'guests'

urlpatterns = [
    path('rsvp/<uuid:token>/', views.RSVPView.as_view(), name='rsvp'),
    path('event/<int:event_id>/list/', views.GuestListView.as_view(), name='guest_list'),
    path('event/<int:event_id>/export/csv/', views.ExportGuestsCSVView.as_view(), name='export_csv'),
    path('event/<int:event_id>/export/excel/', views.ExportGuestsExcelView.as_view(), name='export_excel'),
]