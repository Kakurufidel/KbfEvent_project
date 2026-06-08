from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('create/', views.EventCreateView.as_view(), name='event_create'),
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('<slug:slug>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    
    path('<slug:slug>/rsvp/<str:token>/', views.RSVPFormView.as_view(), name='rsvp_form'),
    path('<slug:slug>/join/<str:token>/', views.JoinCoOrganizerView.as_view(), name='join_coorganizer'),
]