"""Django admin configuration for core models."""
from django.contrib import admin
from .models import Customer, Appointment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'created_at']
    search_fields = ['name', 'phone', 'email']
    list_filter = ['created_at']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'appointment_date', 'service', 'status', 'created_at']
    list_filter = ['status', 'appointment_date', 'created_at']
    search_fields = ['customer__name', 'customer__phone', 'service']
    date_hierarchy = 'appointment_date'
    readonly_fields = ['created_at', 'updated_at']
