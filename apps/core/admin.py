"""Django admin configuration for core models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import (
    Product, Customer, Appointment, Cart, CartItem, Payment, Order, Cancellation, ActivityLog
)


# Customize User admin to include full name fields
class UserAdmin(BaseUserAdmin):
    """Custom User admin with full name fields."""
    
    # Fields to display in the list view
    list_display = ('username', 'email', 'get_full_name_display', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    
    # Fields to show in the form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fields for add form (creating new users)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )
    
    # Search fields
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Order by username
    ordering = ('username',)
    
    def get_full_name_display(self, obj):
        """Display full name in list view."""
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username
    get_full_name_display.short_description = 'Full Name'


# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'name', 'price', 'category', 'is_active', 'created_at']
    search_fields = ['product_id', 'name', 'category']
    list_filter = ['category', 'is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['category', 'name']


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


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_id', 'created_at']
    search_fields = ['customer_id']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'product_id', 'name', 'quantity', 'price', 'created_at']
    search_fields = ['product_id', 'name', 'cart__customer_id']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'mobile_number', 'amount', 'payment_method', 'status', 'otp_verified', 'created_at']
    search_fields = ['mobile_number', 'transaction_id', 'otp_code']
    list_filter = ['status', 'payment_method', 'otp_verified', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'transaction_id', 'total', 'status', 'created_at']
    search_fields = ['order_id', 'transaction_id']
    list_filter = ['status', 'created_at']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(Cancellation)
class CancellationAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'order', 'customer_phone', 'cancellation_type', 'status', 'created_at']
    search_fields = ['request_id', 'order__order_id', 'customer_phone', 'reason']
    list_filter = ['status', 'cancellation_type', 'created_at']
    readonly_fields = ['request_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'action', 'customer_name', 'customer_id', 'created_at']
    search_fields = ['action', 'customer_name', 'customer_id']
    list_filter = ['activity_type', 'created_at']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
