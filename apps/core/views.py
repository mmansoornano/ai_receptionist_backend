"""API views for core models."""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer, Appointment
from .serializers import CustomerSerializer, AppointmentSerializer
from django.utils import timezone
from django.db.models import Q


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer model."""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['created_at', 'name']


class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Appointment model."""
    queryset = Appointment.objects.select_related('customer').all()
    serializer_class = AppointmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer']
    search_fields = ['customer__name', 'service']
    ordering_fields = ['appointment_date', 'created_at']

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments."""
        upcoming = self.queryset.filter(
            appointment_date__gte=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date')
        page = self.paginate_queryset(upcoming)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
