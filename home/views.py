from django.shortcuts import render, redirect
from .models import ParkingSpace
def index(request):
    parking_spaces = ParkingSpace.objects.all()
    return render(request, 'home/index.html', {'parking_spaces': parking_spaces})
def parked_cars(request):
    return render(request, 'menu/parked_cars.html')
