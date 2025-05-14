from django.db import models
from django.utils.timezone import now
import uuid

class User(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('customer', 'Normal User'),
    )
    
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)  # Cho phép null và blank
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    class Meta:
        db_table = 'users'