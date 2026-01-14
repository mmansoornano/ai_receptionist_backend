"""URLs for core app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, AppointmentViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'appointments', AppointmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
