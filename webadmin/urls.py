from django.urls import path
from . import views

urlpatterns = [
    path('admin-home/', views.index, name='index'),
    path('admin-home/traffic-data/', views.traffic_data, name='traffic_data'),
    path('parked-cars/', views.parked_cars, name='parked_cars'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('exit-vehicle/', views.exit_vehicle, name='exit_vehicle'),
    path('history/', views.vehicle_history, name='vehicle_history'),
    path('check_license_plate/', views.check_license_plate, name='check_license_plate'),
    path('check_phone/', views.check_phone, name='check_phone'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('api/users/<str:user_id>/update/', views.update_user, name='update_user'),
    path('vehicle/<str:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicle/<str:vehicle_id>/update-image/', views.update_vehicle_image, name='update_vehicle_image'),
    path('manage-vehicles/', views.manage_vehicles, name='manage_vehicles'),
    path('manage-parking-spaces/', views.manage_parking_spaces, name='manage_parking_spaces'),
    path('add-parking-space/', views.add_parking_space, name='add_parking_space'),
    path('delete-parking-space/<str:space_id>/', views.delete_parking_space, name='delete_parking_space'),
    path('update-parking-space/<str:space_id>/', views.update_parking_space, name='update_parking_space'),

    # Quản lý tài chính
    path('financial-overview/', views.financial_overview, name='financial_overview'),
    path('manage-user-balance/', views.manage_user_balance, name='manage_user_balance'),
    path('user/<str:user_id>/adjust-balance/', views.adjust_user_balance, name='adjust_user_balance'),
    path('transaction-history/', views.transaction_history, name='transaction_history'),
    path('payment-management/', views.payment_management, name='payment_management'),
    path('payment/<int:payment_id>/mark-paid/', views.mark_payment_paid, name='mark_payment_paid'),
    path('user/<str:user_id>/financial-detail/', views.user_financial_detail, name='user_financial_detail'),
]