from django.db import models
from django.utils.timezone import now
import uuid
from account.models import User



class ParkingSpace(models.Model):
    space_number = models.CharField(max_length=10, unique=True)
    level = models.CharField(max_length=10)
    is_occupied = models.IntegerField(default=0)  # 0 = False, 1 = True

    def __str__(self):
        return f"Space {self.space_number} - Level {self.level}"
    class Meta:
       db_table = 'parkingspace'

        
        
class History(models.Model):
    id = models.AutoField(primary_key=True)
    plate_number = models.CharField(max_length=20)
    time_in = models.DateTimeField()
    time_out = models.DateTimeField(null=True, blank=True)
    parking_space = models.ForeignKey(ParkingSpace, on_delete=models.SET_NULL, null=True, blank=True)

    def get_parking_duration(self):
        """Tính thời gian đỗ xe (giờ)"""
        if not self.time_out:
            return None
        duration = self.time_out - self.time_in
        hours = duration.total_seconds() / 3600
        return round(hours, 1)
    
    def get_vehicle(self):
        """Lấy thông tin xe từ biển số"""
        try:
            return Vehicle.objects.get(license_plate=self.plate_number)
        except Vehicle.DoesNotExist:
            return None
    
    def get_user(self):
        """Lấy thông tin người dùng thông qua xe"""
        vehicle = self.get_vehicle()
        if vehicle:
            return vehicle.user
        return None

    def __str__(self):
        return f"Lịch sử gửi xe của {self.plate_number} lúc {self.time_in}"
    
    class Meta:
        db_table = 'histories'
        
class Vehicle(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4, editable=False)
    license_plate = models.CharField(max_length=20, unique=True)
    
    vehicle_type = models.CharField(max_length=50)
    image_path = models.CharField(max_length=255, null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.license_plate} - {self.vehicle_type}"
    
    class Meta:
        db_table = 'vehicles'

