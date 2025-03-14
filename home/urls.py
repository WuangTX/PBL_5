from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('parked-cars/', views.parked_cars, name='parked_cars'),
    
]