from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]
