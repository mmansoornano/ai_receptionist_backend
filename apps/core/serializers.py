"""DRF serializers for core models."""
from rest_framework import serializers
from .models import Customer, Appointment, Cart, CartItem, Payment, Order, Cancellation
from .product_catalog import get_product_name, get_product_price, is_valid_product
from django.db.models import Sum


class CustomerSerializer(serializers.ModelSerializer):
    customer_id = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    last_order_date = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'name', 'phone', 'email', 'preferences',
            'total_orders', 'total_spent', 'last_order_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_id', 'created_at', 'updated_at', 'total_orders', 'total_spent', 'last_order_date']

    def get_customer_id(self, obj):
        """Get customer ID as number - returns user.id if customer is linked to user, otherwise obj.id."""
        return obj.user.id if obj.user else (obj.id if obj.id else None)

    def get_total_orders(self, obj):
        """Get total orders count."""
        try:
            # Count orders linked via payments
            from .models import Payment, Order
            payments = Payment.objects.filter(mobile_number=obj.phone)
            order_ids = payments.values_list('order_id', flat=True).distinct()
            return Order.objects.filter(id__in=order_ids).count()
        except Exception:
            return 0

    def get_total_spent(self, obj):
        """Get total amount spent."""
        try:
            from .models import Payment
            total = Payment.objects.filter(
                mobile_number=obj.phone,
                status='confirmed'
            ).aggregate(total=Sum('amount'))['total']
            return float(total) if total else 0.0
        except Exception:
            return 0.0

    def get_last_order_date(self, obj):
        """Get last order date."""
        try:
            from .models import Payment, Order
            payments = Payment.objects.filter(mobile_number=obj.phone).order_by('-created_at')
            if payments.exists():
                payment = payments.first()
                if payment.order:
                    return payment.order.created_at
            return None
        except Exception:
            return None


class CustomerCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating customer."""
    customer_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=True, max_length=20)


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


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items matching API spec."""
    item_id = serializers.IntegerField(source='id', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['item_id', 'product_id', 'name', 'price', 'quantity', 'subtotal']
        read_only_fields = ['item_id', 'name']

    def get_subtotal(self, obj):
        """Calculate item subtotal."""
        return float(obj.get_subtotal())


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart matching API spec."""
    cart_id = serializers.CharField(source='id', read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['cart_id', 'items', 'total', 'created_at', 'updated_at']
        read_only_fields = ['cart_id', 'created_at', 'updated_at']

    def get_total(self, obj):
        """Calculate cart total."""
        return float(obj.get_total())


class AddCartItemSerializer(serializers.Serializer):
    """Serializer for adding item to cart matching API spec."""
    product_id = serializers.CharField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)
    customer_id = serializers.CharField(required=False, default='anonymous')

    def validate_product_id(self, value):
        """Validate product ID exists in catalog."""
        if not is_valid_product(value):
            raise serializers.ValidationError(f"Invalid product_id: {value}")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item matching API spec."""
    quantity = serializers.IntegerField(required=True, min_value=1)
    customer_id = serializers.CharField(required=False, default='anonymous')


class PaymentOTPSendSerializer(serializers.Serializer):
    """Serializer for sending OTP matching API spec."""
    mobile_number = serializers.CharField(required=True, max_length=20)


class PaymentOTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying OTP matching API spec."""
    mobile_number = serializers.CharField(required=True, max_length=20)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)


class PaymentConfirmSerializer(serializers.Serializer):
    """Serializer for confirming payment matching API spec."""
    mobile_number = serializers.CharField(required=True, max_length=20)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2, min_value=0)
    order_id = serializers.CharField(required=False, allow_blank=True)


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer for payment list matching API spec."""
    id = serializers.CharField(source='id', read_only=True)
    payment_id = serializers.CharField(source='id', read_only=True)
    order_id = serializers.SerializerMethodField()
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    method = serializers.CharField(source='payment_method', read_only=True)
    payment_method = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    transaction_id = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'order_id', 'customer_id', 'customer_name',
            'amount', 'currency', 'method', 'payment_method', 'status',
            'transaction_id', 'date', 'created_at'
        ]
        read_only_fields = ['id', 'payment_id', 'created_at']

    def get_order_id(self, obj):
        """Get order ID."""
        return obj.order.order_id if obj.order else None

    def get_customer_id(self, obj):
        """Get customer ID."""
        return f"customer_{obj.id}"  # Simplified

    def get_customer_name(self, obj):
        """Get customer name."""
        return obj.mobile_number  # Use phone as name

    def get_currency(self, obj):
        """Get currency."""
        return 'PKR'

    def get_payment_method(self, obj):
        """Get payment method display name."""
        method_map = {
            'easypaisa': 'EasyPaisa',
            'jazzcash': 'JazzCash',
            'cash': 'Cash'
        }
        return method_map.get(obj.payment_method, obj.payment_method.title())

    def get_status(self, obj):
        """Get payment status."""
        status_map = {
            'confirmed': 'completed',
            'otp_verified': 'pending',
            'otp_sent': 'pending',
            'pending': 'pending',
            'failed': 'failed'
        }
        return status_map.get(obj.status, obj.status)


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer for single payment matching API spec."""
    id = serializers.CharField(source='id', read_only=True)
    payment_id = serializers.CharField(source='id', read_only=True)
    order_id = serializers.SerializerMethodField()
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    method = serializers.CharField(source='payment_method', read_only=True)
    payment_method = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    transaction_id = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'order_id', 'customer_id', 'customer_name',
            'amount', 'currency', 'method', 'payment_method', 'status',
            'transaction_id', 'date', 'created_at'
        ]
        read_only_fields = ['id', 'payment_id', 'created_at']

    def get_order_id(self, obj):
        """Get order ID."""
        return obj.order.order_id if obj.order else None

    def get_customer_id(self, obj):
        """Get customer ID."""
        return f"customer_{obj.id}"

    def get_customer_name(self, obj):
        """Get customer name."""
        return obj.mobile_number

    def get_currency(self, obj):
        """Get currency."""
        return 'PKR'

    def get_payment_method(self, obj):
        """Get payment method display name."""
        method_map = {
            'easypaisa': 'EasyPaisa',
            'jazzcash': 'JazzCash',
            'cash': 'Cash'
        }
        return method_map.get(obj.payment_method, obj.payment_method.title())

    def get_status(self, obj):
        """Get payment status."""
        status_map = {
            'confirmed': 'completed',
            'otp_verified': 'pending',
            'otp_sent': 'pending',
            'pending': 'pending',
            'failed': 'failed'
        }
        return status_map.get(obj.status, obj.status)


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list matching API spec."""
    id = serializers.CharField(source='order_id', read_only=True)
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    service_type = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='created_at', read_only=True)
    amount = serializers.DecimalField(source='total', max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer_id', 'customer_name', 'service', 'service_type',
            'date', 'status', 'amount', 'currency', 'payment_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at']

    def get_customer_id(self, obj):
        """Get customer ID from payment."""
        try:
            payment = obj.payments.first()
            if payment:
                # Extract customer from payment mobile_number or create customer_id
                return f"customer_{payment.id}"  # Simplified
        except:
            pass
        return None

    def get_customer_name(self, obj):
        """Get customer name."""
        # Try to get from payment
        try:
            payment = obj.payments.first()
            if payment:
                return payment.mobile_number  # Use phone as name fallback
        except:
            pass
        return None

    def get_service(self, obj):
        """Get service name from order items."""
        if obj.items and len(obj.items) > 0:
            # Return first item name or concatenate all
            item_names = [item.get('name', '') for item in obj.items if item.get('name')]
            return ', '.join(item_names[:3])  # First 3 items
        return 'Order'

    def get_service_type(self, obj):
        """Get service type."""
        if obj.items and len(obj.items) > 0:
            # Determine type from first item
            first_item = obj.items[0]
            product_id = first_item.get('product_id', '')
            if 'protein-bar' in product_id:
                return 'protein_bar'
            elif 'granola' in product_id:
                return 'granola'
            elif 'cookie' in product_id:
                return 'cookie'
            elif 'gift-box' in product_id:
                return 'gift_box'
        return 'product'

    def get_currency(self, obj):
        """Get currency."""
        return 'PKR'  # Default to PKR for Pakistan

    def get_payment_status(self, obj):
        """Get payment status from linked payment."""
        try:
            payment = obj.payments.first()
            if payment:
                if payment.status == 'confirmed':
                    return 'paid'
                elif payment.status == 'failed':
                    return 'failed'
        except:
            pass
        return 'pending'


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for single order matching API spec."""
    id = serializers.CharField(source='order_id', read_only=True)
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    service_type = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='created_at', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    amount = serializers.DecimalField(source='total', max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer_id', 'customer_name', 'customer_email', 'customer_phone',
            'service', 'service_type', 'date', 'duration_minutes', 'status', 'amount', 'currency',
            'payment_status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at']

    def get_customer_id(self, obj):
        """Get customer ID from payment."""
        try:
            payment = obj.payments.first()
            if payment:
                return f"customer_{payment.id}"
        except:
            pass
        return None

    def get_customer_name(self, obj):
        """Get customer name."""
        try:
            payment = obj.payments.first()
            if payment:
                return payment.mobile_number
        except:
            pass
        return None

    def get_customer_email(self, obj):
        """Get customer email."""
        return None  # Not stored in current model

    def get_customer_phone(self, obj):
        """Get customer phone."""
        try:
            payment = obj.payments.first()
            if payment:
                return payment.mobile_number
        except:
            pass
        return None

    def get_service(self, obj):
        """Get service name."""
        if obj.items and len(obj.items) > 0:
            item_names = [item.get('name', '') for item in obj.items if item.get('name')]
            return ', '.join(item_names)
        return 'Order'

    def get_service_type(self, obj):
        """Get service type."""
        if obj.items and len(obj.items) > 0:
            first_item = obj.items[0]
            product_id = first_item.get('product_id', '')
            if 'protein-bar' in product_id:
                return 'protein_bar'
            elif 'granola' in product_id:
                return 'granola'
            elif 'cookie' in product_id:
                return 'cookie'
            elif 'gift-box' in product_id:
                return 'gift_box'
        return 'product'

    def get_duration_minutes(self, obj):
        """Get duration (not applicable for e-commerce, return None)."""
        return None

    def get_currency(self, obj):
        """Get currency."""
        return 'PKR'

    def get_payment_status(self, obj):
        """Get payment status."""
        try:
            payment = obj.payments.first()
            if payment:
                if payment.status == 'confirmed':
                    return 'paid'
                elif payment.status == 'failed':
                    return 'failed'
        except:
            pass
        return 'pending'

    def get_notes(self, obj):
        """Get notes."""
        return None  # Not stored in current model


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders matching API spec."""
    order_id = serializers.CharField(source='order_id', read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'transaction_id', 'items', 'total', 'status', 'created_at'
        ]
        read_only_fields = ['order_id', 'created_at']


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating order matching API spec."""
    cart_data = serializers.DictField(required=False, allow_null=True)
    customer_id = serializers.CharField(required=False, allow_blank=True)
    transaction_id = serializers.CharField(required=True, max_length=255)
    
    def validate(self, data):
        """Ensure either cart_data or customer_id is provided."""
        cart_data = data.get('cart_data')
        customer_id = data.get('customer_id', '').strip()
        
        if not cart_data and not customer_id:
            raise serializers.ValidationError(
                "Either 'cart_data' or 'customer_id' must be provided"
            )
        return data


class CancellationSerializer(serializers.Serializer):
    """Serializer for cancellation response matching API spec."""
    request_id = serializers.CharField()
    message = serializers.CharField()
    customer_service_phone = serializers.CharField()


class SubmitCancellationSerializer(serializers.Serializer):
    """Serializer for submitting cancellation request matching API spec."""
    order_id = serializers.CharField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
