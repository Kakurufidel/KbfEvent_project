from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('create/', views.EventCreateView.as_view(), name='create_event'),
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('<slug:slug>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    
    path('<slug:slug>/rsvp/<str:token>/', views.RSVPFormView.as_view(), name='rsvp_form'),
    path('<slug:slug>/join/<str:token>/', views.JoinCoOrganizerView.as_view(), name='join_coorganizer'),
    
    path('<int:event_id>/tables/', views.TableListView.as_view(), name='table_list'),
    path('<int:event_id>/tables/create/', views.TableCreateView.as_view(), name='table_create'),
    path('auto-assign/<int:event_id>/', views.AutoAssignTablesView.as_view(), name='auto_assign_tables'),
]