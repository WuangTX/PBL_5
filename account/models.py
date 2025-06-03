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
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Số dư tài khoản 
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    class Meta:
        db_table = 'users'
        
class TransactionHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20)  # Bỏ choices
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, default='COMPLETED')  # Bỏ choices
    payment = models.ForeignKey('webadmin.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"Giao dịch #{self.id} của {self.user.name} - {self.transaction_type} - {self.amount} VNĐ"

    class Meta:
        db_table = 'transaction_history'
        indexes = [
            models.Index(fields=['payment'])
        ]