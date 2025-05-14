from django.urls import path
from . import views

urlpatterns = [
    path('admin-home/', views.index, name='index'),
    path('parked-cars/', views.parked_cars, name='parked_cars'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('exit-vehicle/', views.exit_vehicle, name='exit_vehicle'),
    path('history/', views.vehicle_history, name='vehicle_history'),
    path('check_license_plate/', views.check_license_plate, name='check_license_plate'),
    path('check_phone/', views.check_phone, name='check_phone'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('api/users/<str:user_id>/update/', views.update_user, name='update_user'),
    path('vehicle/<str:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('manage-vehicles/', views.manage_vehicles, name='manage_vehicles'),
]