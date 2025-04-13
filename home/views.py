from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import requests
from .models import ParkingSpace
def index(request):
    parking_spaces = ParkingSpace.objects.all()
    return render(request, 'home/index.html', {'parking_spaces': parking_spaces})
def parked_cars(request):
    return render(request, 'menu/parked_cars.html')
#@csrf_exempt
def add_vehicle(request):
    if request.method == 'POST':
        license_plate = request.POST.get('license_plate')
        vehicle_type = request.POST.get('vehicle_type')
        owner_name = request.POST.get('owner_name')
        phone_number = request.POST.get('phone_number')
        notes = request.POST.get('notes')
        upload_later = request.POST.get('uploadLater')

        image = request.FILES.get('vehicle_image')
        files = {}

        if image and not upload_later:
            files['vehicle_image'] = (image.name, image.read(), image.content_type)

        data = {
            'license_plate': license_plate,
            'vehicle_type': vehicle_type,
            'owner_name': owner_name,
            'phone_number': phone_number,
            'notes': notes,
            'uploadLater': upload_later or ""
        }

        try:
            response = requests.post("http://127.0.0.1:5000/add_]vehicle", data=data, files=files)
            if response.status_code == 200:
                return redirect('add_vehicle')
            return HttpResponse("Flask server returned an error", status=500)
        except Exception as e:
            return HttpResponse(f"Error connecting to Flask server: {e}", status=500)

    return render(request, 'menu/add_vehicle.html')