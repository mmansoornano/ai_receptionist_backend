"""DRF serializers for core models."""
from rest_framework import serializers
from .models import Customer, Appointment


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'preferences', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Appointment
        fields = [
            'id', 'customer', 'customer_id', 'appointment_date', 'service',
            'status', 'notes', 'calendar_event_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
