"""URLs for core app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, AppointmentViewSet, CartViewSet,
    PaymentViewSet, OrderViewSet, CancellationViewSet, ProductViewSet
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'cancellations', CancellationViewSet, basename='cancellation')

# Payment endpoints - API spec uses /api/payment/ for OTP actions
# but /api/payments/ for list/get, so we register both
payment_viewset = PaymentViewSet.as_view({
    'get': 'list',
    'post': 'list'  # For custom actions
})

urlpatterns = [
    path('', include(router.urls)),
    # Payment OTP endpoints at /api/payment/ (matching API spec)
    path('payment/', include([
        path('otp/send/', PaymentViewSet.as_view({'post': 'send_otp'}), name='payment-otp-send'),
        path('otp/verify/', PaymentViewSet.as_view({'post': 'verify_otp'}), name='payment-otp-verify'),
        path('easypaisa/confirm/', PaymentViewSet.as_view({'post': 'confirm_easypaisa'}), name='payment-easypaisa-confirm'),
    ])),
]
