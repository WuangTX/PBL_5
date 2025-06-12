from django.urls import path
from . import views

urlpatterns = [
    path('', views.vehicle_management_view, name='vehicle_management'),
    path('add/', views.add_vehicle_view, name='add_vehicle'),
    path('check-license/', views.check_license_plate, name='check_license_plate'),
    path('detail/<str:vehicle_id>/', views.vehicle_detail_view, name='vehicle_detail'),
    path('status/<str:vehicle_id>/', views.vehicle_status_api, name='vehicle_status_api'),
]
