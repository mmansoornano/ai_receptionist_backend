"""Core models for customers and appointments."""
from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
import random
from datetime import timedelta


class Product(models.Model):
    """Product model for catalog."""
    product_id = models.CharField(max_length=255, unique=True, help_text="Unique product identifier")
    name = models.CharField(max_length=255, help_text="Product display name")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Product price")
    description = models.TextField(blank=True, null=True, help_text="Product description")
    category = models.CharField(max_length=100, blank=True, null=True, help_text="Product category")
    is_active = models.BooleanField(default=True, help_text="Whether product is available")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_id})"


class Customer(models.Model):
    """Customer model.
    
    Customer is linked to User via OneToOneField. For access checks, use customer.user.id.
    When creating customers, ensure customer.user.id == user.id.
    Phone and email are not unique to allow multiple customers with the same phone/email if needed.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', null=True, blank=True, help_text="One-to-one relationship with User")
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number (not unique)")
    email = models.EmailField(validators=[EmailValidator()], blank=True, null=True, help_text="Email address (not unique)")
    preferences = models.JSONField(default=dict, blank=True)
    delivery_address = models.TextField(blank=True, null=True, help_text="Delivery address")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Only ID is unique - no other unique constraints

    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    @property
    def customer_id(self):
        """Return user.id as customer_id for API compatibility."""
        return self.user.id if self.user else self.id


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


class Cart(models.Model):
    """Shopping cart model."""
    customer_id = models.CharField(max_length=255, unique=True, default='anonymous', help_text="Customer ID or 'anonymous'")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart {self.id} - {self.customer_id}"

    def get_total(self):
        """Calculate total cart value."""
        return sum(item.price * item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Cart item model."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255, help_text="Product name")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        unique_together = ['cart', 'product_id']

    def __str__(self):
        return f"{self.name} x{self.quantity} - Cart {self.cart.id}"

    def get_subtotal(self):
        """Calculate item subtotal."""
        return self.price * self.quantity


class Payment(models.Model):
    """Payment model for OTP and payment processing."""
    PAYMENT_METHOD_CHOICES = [
        ('easypaisa', 'EasyPaisa'),
        ('jazzcash', 'JazzCash'),
        ('cash', 'Cash'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    mobile_number = models.CharField(max_length=20, help_text="Mobile number for payment")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='easypaisa')
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.mobile_number} - {self.amount}"

    def generate_otp(self):
        """Generate a 6-digit OTP and set expiry (5 minutes)."""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timedelta(minutes=5)
        self.status = 'otp_sent'
        self.save()
        return self.otp_code

    def verify_otp(self, otp_code):
        """Verify OTP code."""
        if not self.otp_code:
            return False
        if timezone.now() > self.otp_expires_at:
            return False
        if self.otp_code == otp_code:
            self.otp_verified = True
            self.status = 'otp_verified'
            self.save()
            return True
        return False


class Order(models.Model):
    """Order model."""
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order_id = models.CharField(max_length=50, unique=True, editable=False, help_text="Order ID like ORD123456")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    items = models.JSONField(default=list, help_text="List of order items with product_id, name, quantity, price")
    total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id}"

    def save(self, *args, **kwargs):
        """Generate unique order ID on creation."""
        if not self.order_id:
            # Generate ORD followed by 6 digits
            import random
            self.order_id = f"ORD{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)


class Cancellation(models.Model):
    """Cancellation request model."""
    CANCELLATION_TYPE_CHOICES = [
        ('customer_request', 'Customer Request'),
        ('out_of_stock', 'Out of Stock'),
        ('payment_failed', 'Payment Failed'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='cancellations')
    request_id = models.CharField(max_length=50, unique=True, editable=False, help_text="Cancellation request ID like CAN123456")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    cancellation_type = models.CharField(max_length=30, choices=CANCELLATION_TYPE_CHOICES, default='customer_request')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cancellation {self.request_id} - Order {self.order.order_id} - {self.status}"

    def save(self, *args, **kwargs):
        """Generate unique request ID on creation."""
        if not self.request_id:
            import random
            self.request_id = f"CAN{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)


class ActivityLog(models.Model):
    """Activity log model for tracking admin dashboard activities."""
    ACTIVITY_TYPE_CHOICES = [
        ('booking', 'Booking'),
        ('cancellation', 'Cancellation'),
        ('payment', 'Payment'),
        ('conversation', 'Conversation'),
    ]

    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES, help_text="Type of activity")
    action = models.CharField(max_length=255, help_text="Human-readable description of the activity")
    customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="Customer identifier")
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text="Customer name")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional context data")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.activity_type} - {self.action} - {self.created_at}"


def log_activity(activity_type, action, customer_id=None, customer_name=None, metadata=None):
    """Helper function to create activity log entries."""
    try:
        ActivityLog.objects.create(
            activity_type=activity_type,
            action=action,
            customer_id=customer_id,
            customer_name=customer_name,
            metadata=metadata or {}
        )
    except Exception:
        # Silently fail if logging fails - don't break the main operation
        pass
