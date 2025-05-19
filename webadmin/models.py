from django.db import models
from django.utils.timezone import now
import uuid
from account.models import User

class MySQLUUIDField(models.CharField):
    """
    Custom field to handle UUIDs in MySQL properly.
    Instead of using native UUID field (which causes issues with MySQL),
    we use CharField to store UUID as string in a MySQL-compatible format.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 36
        super().__init__(*args, **kwargs)
    
    def get_prep_value(self, value):
        # Convert UUID to string before storing in DB
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return value
    
    def to_python(self, value):
        # Convert string to UUID when retrieving from DB
        if value is None or value == '':
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None


class ParkingSpace(models.Model):
    
    id = MySQLUUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space_number = models.CharField(max_length=10)
    level = models.IntegerField()
    is_occupied = models.IntegerField(default=0)  # 0 = False, 1 = True
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Space {self.space_number} - Level {self.level}"
        
    class Meta:
        db_table = 'parkingspace'
        unique_together = ('level', 'space_number')  # Mỗi cặp (level, space_number) phải là duy nhất

        
        
class History(models.Model):
    id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='histories')
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
    
    def get_user(self):
        """Lấy thông tin người dùng thông qua xe"""
        if self.vehicle:
            return self.vehicle.user
        return None

    def __str__(self):
        return f"Lịch sử gửi xe của {self.vehicle.license_plate if self.vehicle else 'unknown'} lúc {self.time_in}"
    
    class Meta:
        db_table = 'histories'
        
class Vehicle(models.Model):
    id = MySQLUUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_plate = models.CharField(max_length=20, unique=True)
    
    vehicle_type = models.CharField(max_length=50)
    image_path = models.CharField(max_length=255, null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.license_plate} - {self.vehicle_type}"
    
    class Meta:
        db_table = 'vehicles'

