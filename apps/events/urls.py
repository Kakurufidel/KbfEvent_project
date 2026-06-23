from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('create/', views.EventCreateView.as_view(), name='create_event'),
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('<slug:slug>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    
    # RSVP – lien unique pour tous les invités
    path('<slug:slug>/rsvp/<str:token>/', views.RSVPFormView.as_view(), name='rsvp_form'),
    
    # Co-organisateur – lien unique pour les co-organisateurs
    path('<slug:slug>/join/<str:token>/', views.JoinCoOrganizerView.as_view(), name='join_coorganizer'),
    path('join/<str:short_code>/', views.JoinCoOrganizerShortCodeView.as_view(), name='join_coorganizer_short'),
    
    # Tables
    path('<int:event_id>/tables/', views.TableListView.as_view(), name='table_list'),
    path('<int:event_id>/tables/create/', views.TableCreateView.as_view(), name='table_create'),
    path('tables/<int:pk>/edit/', views.TableUpdateView.as_view(), name='table_update'),
    path('tables/<int:pk>/delete/', views.TableDeleteView.as_view(), name='table_delete'),
    path('auto-assign/<int:event_id>/', views.AutoAssignTablesView.as_view(), name='auto_assign_tables'),
    path('<int:event_id>/tables-pdf/', views.TablesPDFView.as_view(), name='tables_pdf'),
    
    path('<int:event_id>/export-tables-csv/', views.ExportTablesCSVView.as_view(), name='export_tables_csv'),
    path('<int:event_id>/export-tables-excel/', views.ExportTablesExcelView.as_view(), name='export_tables_excel'),

    # Révision manuelle des tables
    path('<int:event_id>/assign-table/', views.AssignGuestTableView.as_view(), name='assign_guest_table'),

    ]