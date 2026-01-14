"""Core models for customers and appointments."""
from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone


class Customer(models.Model):
    """Customer model."""
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(validators=[EmailValidator()], blank=True, null=True)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Appointment(models.Model):
    """Appointment model."""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    service = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date']

    def __str__(self):
        return f"{self.customer.name} - {self.appointment_date.strftime('%Y-%m-%d %H:%M')}"

    def is_upcoming(self):
        """Check if appointment is in the future."""
        return self.appointment_date > timezone.now()
