from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('create/', views.EventCreateView.as_view(), name='create_event'),
    # Changement: utiliser slug au lieu de event_id car votre modèle Event utilise slug
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='edit_event'),
    path('<slug:slug>/delete/', views.EventDeleteView.as_view(), name='delete_event'),
    path('join/<slug:slug>/<str:token>/', views.JoinCoOrganizerView.as_view(), name='join_coorganizer'),
]