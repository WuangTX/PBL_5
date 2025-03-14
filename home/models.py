from django.db import models

class ParkingLot(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    total_spaces = models.IntegerField()
    available_spaces = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return self.name

class ParkingSpot(models.Model):
    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE)
    spot_number = models.IntegerField()
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return f'Spot {self.spot_number} in {self.lot.name}'

class ParkingSpace(models.Model):
    space_number = models.CharField(max_length=10, unique=True)
    level = models.CharField(max_length=10)
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Space {self.space_number} - Level {self.level}"

class Vehicle(models.Model):
    license_plate = models.CharField(max_length=20, unique=True)
    parking_space = models.ForeignKey(ParkingSpace, null=True, on_delete=models.SET_NULL)
    entry_time = models.DateTimeField(auto_now_add=True)
    exit_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.license_plate