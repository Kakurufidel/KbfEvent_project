from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Packs CRUD
    path('event/<int:event_id>/packs/', views.BeveragePackListView.as_view(), name='beveragepack_list'),
    path('event/<int:event_id>/packs/create/', views.BeveragePackCreateView.as_view(), name='beveragepack_create'),
    path('packs/<int:pk>/edit/', views.BeveragePackUpdateView.as_view(), name='beveragepack_update'),
    path('packs/<int:pk>/delete/', views.BeveragePackDeleteView.as_view(), name='beveragepack_delete'),
    

    # Estimation
    path('event/<int:event_id>/estimation/', views.EstimationDashboardView.as_view(), name='estimation'),

    # Exports
    path('event/<int:event_id>/devis/', views.ExportDevisPDFView.as_view(), name='export_devis'),
]