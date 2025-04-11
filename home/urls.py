from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('parked-cars/', views.parked_cars, name='parked_cars'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    
]