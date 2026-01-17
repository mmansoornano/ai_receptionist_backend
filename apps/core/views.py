"""API views for core models."""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.core.permissions import IsAdmin
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from .models import Customer, Appointment, Cart, CartItem, Payment, Order, Cancellation, Product, log_activity
from .serializers import (
    CustomerSerializer, CustomerCreateSerializer, AppointmentSerializer,
    CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer,
    PaymentOTPSendSerializer, PaymentOTPVerifySerializer, PaymentConfirmSerializer,
    PaymentListSerializer, PaymentDetailSerializer, OrderSerializer, OrderListSerializer,
    OrderDetailSerializer, CreateOrderSerializer, CancellationSerializer, SubmitCancellationSerializer,
    ProductSerializer
)
from .product_catalog import get_product_name, get_product_price, is_valid_product


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer model."""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['created_at', 'name']

    def retrieve(self, request, pk=None):
        """Get customer by ID. GET /api/customers/{id}/"""
        try:
            # Support both numeric ID and "customer_{id}" format for backward compatibility
            customer_id = pk
            if pk and isinstance(pk, str) and pk.startswith('customer_'):
                try:
                    customer_id = int(pk.split('_')[1])
                except (ValueError, IndexError):
                    return JsonResponse({
                        'error': 'Invalid customer ID format'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                customer = Customer.objects.get(id=customer_id)
            except (ValueError, Customer.DoesNotExist):
                return JsonResponse({
                    'error': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(customer)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='me')
    def get_my_customer(self, request):
        """Get current user's customer record. GET /api/customers/me/"""
        try:
            # Get logged-in user
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Try to find customer linked to user via OneToOneField
            try:
                customer = Customer.objects.get(user=user)
            except Customer.DoesNotExist:
                # If customer doesn't exist, create one linked to user
                customer = Customer.objects.create(
                    user=user,
                    name=user.get_full_name() or user.username,
                    email=user.email,
                    phone=f'user_{user.id}'  # Temporary phone number
                )

            serializer = self.get_serializer(customer)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for product catalog."""
    queryset = Product.objects.filter(is_active=True).order_by('category', 'name')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category', 'product_id']
    ordering_fields = ['category', 'name', 'price']

    @action(detail=False, methods=['post'], url_path='address')
    def update_address(self, request):
        """Update delivery address for a customer. POST /api/customers/address/"""
        try:
            address = (request.data.get('delivery_address') or '').strip()
            customer_id = request.data.get('customer_id')
            phone = request.data.get('phone')

            if not address:
                return JsonResponse({
                    'success': False,
                    'error': 'Delivery address is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            customer = None
            if request.user and request.user.is_authenticated and not request.user.is_staff:
                customer = Customer.objects.filter(user=request.user).first()

            if not customer and customer_id:
                customer = Customer.objects.filter(user__id=customer_id).first() or Customer.objects.filter(id=customer_id).first()

            if not customer and phone:
                customer = Customer.objects.filter(phone=phone).first()

            if not customer:
                return JsonResponse({
                    'success': False,
                    'error': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)

            customer.delivery_address = address
            customer.save(update_fields=['delivery_address'])

            serializer = CustomerSerializer(customer)
            return JsonResponse({
                'success': True,
                'customer': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """Create or update customer. POST /api/customers/"""
        try:
            serializer = CustomerCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'error': 'Validation error',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            phone = data['phone']
            name = data['name']
            email = data.get('email', '')
            delivery_address = data.get('delivery_address', '')
            customer_id = data.get('customer_id', '')

            # Get or create customer by phone
            customer, created = Customer.objects.get_or_create(
                phone=phone,
                defaults={'name': name, 'email': email}
            )

            # Update if exists
            if not created:
                customer.name = name
                if email:
                    customer.email = email
                if delivery_address:
                    customer.delivery_address = delivery_address
                customer.save()
            elif delivery_address:
                customer.delivery_address = delivery_address
                customer.save(update_fields=['delivery_address'])

            serializer = CustomerSerializer(customer)
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class CartViewSet(viewsets.ViewSet):
    """ViewSet for cart operations matching API spec."""
    permission_classes = [AllowAny]
    
    def get_cart(self, customer_id='anonymous'):
        """Get or create cart based on customer_id.
        
        Note: For persistence, the same customer_id must be used across requests.
        If customer_id is 'anonymous' or not provided, consider using session-based
        tracking or a persistent identifier from the client.
        """
        # Ensure customer_id is not None or empty
        if not customer_id or customer_id.strip() == '':
            customer_id = 'anonymous'
        
        cart, _ = Cart.objects.get_or_create(customer_id=customer_id)
        return cart
    
    def get_customer_id_from_request(self, request, default='anonymous'):
        """Extract customer_id from request data or query params."""
        # If an authenticated non-admin user is making the request, lock to their ID
        if request.user and request.user.is_authenticated and not request.user.is_staff:
            return str(request.user.id)

        # Try to get from request data (POST body)
        customer_id = None
        if hasattr(request, 'data') and request.data:
            customer_id = request.data.get('customer_id')
        
        # Try to get from query params (GET)
        if not customer_id:
            customer_id = request.GET.get('customer_id')
        
        # Try to get from JSON body if content type is JSON
        if not customer_id and request.content_type == 'application/json':
            try:
                import json
                if hasattr(request, 'body') and request.body:
                    body_data = json.loads(request.body)
                    customer_id = body_data.get('customer_id')
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return customer_id if customer_id else default

    @action(detail=False, methods=['post'], url_path='add')
    def add_item(self, request):
        """Add item to cart. POST /api/cart/add"""
        try:
            serializer = AddCartItemSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            # Get customer_id from request, with fallback to serializer data
            customer_id = self.get_customer_id_from_request(request) or data.get('customer_id', 'anonymous')
            product_id = data['product_id']
            quantity = data['quantity']

            # Get product info from catalog
            if not is_valid_product(product_id):
                # Try to find a similar product (for common variations like "gift-box" -> "gift-box-all-bars")
                similar_products = Product.objects.filter(
                    product_id__icontains=product_id,
                    is_active=True
                )[:1]
                if similar_products.exists():
                    similar_product = similar_products.first()
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid product_id: {product_id}. Did you mean "{similar_product.product_id}"?',
                        'suggested_product_id': similar_product.product_id
                    }, status=status.HTTP_400_BAD_REQUEST)
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid product_id: {product_id}. Product not found in catalog.'
                }, status=status.HTTP_400_BAD_REQUEST)

            product_name = get_product_name(product_id)
            product_price = get_product_price(product_id)
            
            # Validate product info was retrieved
            if not product_name or product_name == product_id:
                return JsonResponse({
                    'success': False,
                    'error': f'Product "{product_id}" not found in catalog'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if product_price is None or product_price == 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Product "{product_id}" has invalid price'
                }, status=status.HTTP_400_BAD_REQUEST)

            cart = self.get_cart(customer_id)

            # Get or create cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product_id=product_id,
                defaults={
                    'name': product_name,
                    'quantity': quantity,
                    'price': product_price
                }
            )

            if not created:
                # Update quantity if item already exists
                cart_item.quantity += quantity
                cart_item.save()

            # Refresh cart from DB to ensure we have latest items
            cart.refresh_from_db()
            
            try:
                cart_serializer = CartSerializer(cart)
                return JsonResponse({
                    'success': True,
                    'cart': cart_serializer.data
                }, status=status.HTTP_201_CREATED)
            except Exception as serialize_error:
                import traceback
                import logging
                from django.conf import settings
                DEBUG = getattr(settings, 'DEBUG', False)
                error_msg = f"Error serializing cart: {str(serialize_error)}"
                if DEBUG:
                    error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
                logger = logging.getLogger(__name__)
                logger.error(f"Cart serializer error: {error_msg}")
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            import traceback
            import logging
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{error_traceback}"
            # Log the error for debugging
            logger = logging.getLogger(__name__)
            logger.error(f"Cart add_item error: {error_msg}\n{error_traceback}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': error_msg if DEBUG else 'An error occurred while adding item to cart',
                'customer_id': customer_id if 'customer_id' in locals() else 'unknown',
                'product_id': product_id if 'product_id' in locals() else 'unknown'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """Get cart contents. GET /api/cart"""
        try:
            customer_id = self.get_customer_id_from_request(request, 'anonymous')

            cart = self.get_cart(customer_id)
            cart_serializer = CartSerializer(cart)
            return JsonResponse({
                'success': True,
                'cart': cart_serializer.data
            })
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['put'], url_path='item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item. PUT /api/cart/item/:id"""
        try:
            serializer = UpdateCartItemSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                cart_item = CartItem.objects.get(id=item_id)
            except CartItem.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Cart item not found'
                }, status=status.HTTP_404_NOT_FOUND)

            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.save()

            cart_serializer = CartSerializer(cart_item.cart)
            return JsonResponse({
                'success': True,
                'cart': cart_serializer.data
            })
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart. DELETE /api/cart/item/:id"""
        try:
            try:
                cart_item = CartItem.objects.get(id=item_id)
                cart = cart_item.cart
                cart_item.delete()
                # Refresh cart from database to get updated items
                cart.refresh_from_db()
            except CartItem.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Cart item not found'
                }, status=status.HTTP_404_NOT_FOUND)

            cart_serializer = CartSerializer(cart)
            return JsonResponse({
                'success': True,
                'cart': cart_serializer.data
            })
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def clear_cart(self, request):
        """Clear cart. DELETE /api/cart"""
        try:
            customer_id = self.get_customer_id_from_request(request, 'anonymous')

            try:
                cart = Cart.objects.get(customer_id=customer_id)
                cart.items.all().delete()
                cart_serializer = CartSerializer(cart)
                return JsonResponse({
                    'success': True,
                    'cart': cart_serializer.data
                })
            except Cart.DoesNotExist:
                # Return empty cart if doesn't exist
                return JsonResponse({
                    'success': True,
                    'cart': {
                        'cart_id': None,
                        'items': [],
                        'total': 0.00,
                        'created_at': None,
                        'updated_at': None
                    }
                })
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentViewSet(viewsets.ViewSet):
    """ViewSet for payment operations matching API spec - admin only."""
    permission_classes = [IsAdmin]

    def list(self, request):
        """List payments with filters. GET /api/payments/"""
        try:
            queryset = Payment.objects.select_related('order').all()

            # Status filter
            status_filter = request.GET.get('status', '')
            if status_filter:
                # Map frontend status to backend status
                status_map = {
                    'completed': 'confirmed',
                    'pending': ['pending', 'otp_sent', 'otp_verified'],
                    'failed': 'failed'
                }
                if status_filter in status_map:
                    backend_status = status_map[status_filter]
                    if isinstance(backend_status, list):
                        queryset = queryset.filter(status__in=backend_status)
                    else:
                        queryset = queryset.filter(status=backend_status)

            # Customer ID filter
            customer_id = request.GET.get('customer_id', '')
            if customer_id:
                try:
                    if customer_id.startswith('customer_'):
                        user_id = int(customer_id.split('_')[1])
                        queryset = queryset.filter(id=user_id)
                    else:
                        queryset = queryset.filter(id=customer_id)
                except (ValueError, IndexError):
                    pass

            # Order ID filter
            order_id = request.GET.get('order_id', '')
            if order_id:
                queryset = queryset.filter(order__order_id=order_id)

            # Date filters
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')
            if date_from:
                from django.utils.dateparse import parse_datetime
                try:
                    date_from_dt = parse_datetime(date_from)
                    if date_from_dt:
                        queryset = queryset.filter(created_at__gte=date_from_dt)
                except:
                    pass
            if date_to:
                from django.utils.dateparse import parse_datetime
                try:
                    date_to_dt = parse_datetime(date_to)
                    if date_to_dt:
                        queryset = queryset.filter(created_at__lte=date_to_dt)
                except:
                    pass

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            payments = queryset[start:end]

            serializer = PaymentListSerializer(payments, many=True)

            # Build pagination response
            next_url = None
            if end < total:
                next_page = page + 1
                next_url = f"{request.build_absolute_uri().split('?')[0]}?page={next_page}&page_size={page_size}"

            previous_url = None
            if page > 1:
                prev_page = page - 1
                previous_url = f"{request.build_absolute_uri().split('?')[0]}?page={prev_page}&page_size={page_size}"

            return JsonResponse({
                'count': total,
                'next': next_url,
                'previous': previous_url,
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Get single payment. GET /api/payments/{id}/"""
        try:
            try:
                payment = Payment.objects.select_related('order').get(id=pk)
            except Payment.DoesNotExist:
                return JsonResponse({
                    'error': 'Payment not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = PaymentDetailSerializer(payment)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='otp/send')
    def send_otp(self, request):
        """Send OTP to mobile. POST /api/payment/otp/send
        
        Optional: Can include customer_id to calculate cart total for payment amount.
        """
        try:
            serializer = PaymentOTPSendSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            mobile_number = data['mobile_number']
            
            # Optional: Get cart total if customer_id is provided
            customer_id = request.data.get('customer_id', '').strip()
            amount = 0
            if customer_id:
                try:
                    cart = Cart.objects.get(customer_id=customer_id)
                    amount = cart.get_total()
                except Cart.DoesNotExist:
                    pass

            # Create payment record (amount will be set later or now if cart found)
            payment = Payment.objects.create(
                mobile_number=mobile_number,
                amount=amount,  # Set to cart total if customer_id provided, else 0
                payment_method='easypaisa'
            )

            # Generate OTP (simulated - returns OTP in response for demo)
            otp_code = payment.generate_otp()

            response_data = {
                'success': True,
                'message': f'OTP sent to {mobile_number}',
                'expires_in_minutes': 5
            }
            
            # Include cart total if customer_id was provided
            if customer_id and amount > 0:
                response_data['cart_total'] = float(amount)
            
            return JsonResponse(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='otp/verify')
    def verify_otp(self, request):
        """Verify OTP. POST /api/payment/otp/verify"""
        try:
            serializer = PaymentOTPVerifySerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            mobile_number = data['mobile_number']
            otp = data['otp']

            # Get latest payment for this mobile number
            try:
                payment = Payment.objects.filter(
                    mobile_number=mobile_number,
                    status__in=['otp_sent', 'otp_verified']
                ).latest('created_at')
            except Payment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'No OTP found for this mobile number'
                }, status=status.HTTP_404_NOT_FOUND)

            # Verify OTP
            if payment.verify_otp(otp):
                return JsonResponse({
                    'success': True,
                    'message': 'OTP verified successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid OTP. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='easypaisa/confirm')
    def confirm_easypaisa(self, request):
        """Confirm EasyPaisa payment. POST /api/payment/easypaisa/confirm"""
        try:
            serializer = PaymentConfirmSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            mobile_number = data['mobile_number']
            amount = data['amount']
            order_id = data.get('order_id', '')

            # Get verified payment
            try:
                payment = Payment.objects.filter(
                    mobile_number=mobile_number,
                    status='otp_verified'
                ).latest('created_at')
            except Payment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'OTP not verified. Please verify OTP first.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate transaction ID (simulated)
            import random
            transaction_id = f"EP{random.randint(100000000, 999999999)}"

            # Confirm payment
            payment.status = 'confirmed'
            payment.transaction_id = transaction_id
            payment.amount = amount
            payment.save()

            # Log activity
            log_activity(
                activity_type='payment',
                action='Payment received',
                customer_id=payment.id,
                customer_name=payment.mobile_number,
                metadata={'transaction_id': transaction_id, 'amount': float(amount), 'payment_method': payment.payment_method}
            )

            return JsonResponse({
                'success': True,
                'transaction_id': transaction_id,
                'amount': float(amount),
                'status': 'completed',
                'message': 'Payment confirmed successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderViewSet(viewsets.ViewSet):
    """ViewSet for order operations matching API spec - admin only."""
    permission_classes = [IsAdmin]

    def list(self, request):
        """List orders with filters. GET /api/orders/"""
        try:
            queryset = Order.objects.prefetch_related('payments').all()

            # Status filter
            status_filter = request.GET.get('status', '')
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Customer ID filter
            customer_id = request.GET.get('customer_id', '')
            if customer_id:
                # customer_id is now a number
                try:
                    customer_id_int = int(customer_id)
                    queryset = queryset.filter(customer__id=customer_id_int)
                except (ValueError, TypeError):
                    pass

            # Date filters
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')
            if date_from:
                from django.utils.dateparse import parse_datetime
                try:
                    date_from_dt = parse_datetime(date_from)
                    if date_from_dt:
                        queryset = queryset.filter(created_at__gte=date_from_dt)
                except:
                    pass
            if date_to:
                from django.utils.dateparse import parse_datetime
                try:
                    date_to_dt = parse_datetime(date_to)
                    if date_to_dt:
                        queryset = queryset.filter(created_at__lte=date_to_dt)
                except:
                    pass

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            orders = queryset[start:end]

            serializer = OrderListSerializer(orders, many=True)

            # Build pagination response
            next_url = None
            if end < total:
                next_page = page + 1
                next_url = f"{request.build_absolute_uri().split('?')[0]}?page={next_page}&page_size={page_size}"

            previous_url = None
            if page > 1:
                prev_page = page - 1
                previous_url = f"{request.build_absolute_uri().split('?')[0]}?page={prev_page}&page_size={page_size}"

            return JsonResponse({
                'count': total,
                'next': next_url,
                'previous': previous_url,
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Get single order. GET /api/orders/{id}/"""
        try:
            try:
                order = Order.objects.prefetch_related('payments').get(order_id=pk)
            except Order.DoesNotExist:
                return JsonResponse({
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = OrderDetailSerializer(order)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """Update order status. PATCH /api/orders/{id}/"""
        try:
            try:
                order = Order.objects.get(order_id=pk)
            except Order.DoesNotExist:
                return JsonResponse({
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            status_value = request.data.get('status')
            if status_value:
                if status_value in dict(Order.ORDER_STATUS_CHOICES):
                    order.status = status_value
                    order.save()
                else:
                    return JsonResponse({
                        'error': f'Invalid status: {status_value}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            serializer = OrderDetailSerializer(order)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='create')
    def create_order(self, request):
        """Create order after payment. POST /api/orders/create
        
        Accepts either:
        1. cart_data + transaction_id (original API spec)
        2. customer_id + transaction_id (convenience - fetches cart automatically)
        """
        try:
            serializer = CreateOrderSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            cart_data = data.get('cart_data')
            customer_id = data.get('customer_id', '').strip()
            transaction_id = data['transaction_id']

            # If cart_data not provided, fetch cart using customer_id
            if not cart_data and customer_id:
                try:
                    cart = Cart.objects.get(customer_id=customer_id)
                    if not cart.items.exists():
                        return JsonResponse({
                            'success': False,
                            'error': 'Cart is empty'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Convert cart to cart_data format
                    cart_serializer = CartSerializer(cart)
                    cart_data = cart_serializer.data
                except Cart.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': f'Cart not found for customer_id: {customer_id}'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Extract cart items from cart_data
            cart_items = cart_data.get('items', [])
            if not cart_items:
                return JsonResponse({
                    'success': False,
                    'error': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create order items list
            order_items = []
            total = 0.0
            for item in cart_items:
                order_items.append({
                    'item_id': item.get('item_id'),
                    'product_id': item.get('product_id'),
                    'name': item.get('name'),
                    'quantity': item.get('quantity'),
                    'price': float(item.get('price', 0)),
                    'subtotal': float(item.get('subtotal', 0))
                })
                total += float(item.get('subtotal', 0))

            # Create order
            order = Order.objects.create(
                transaction_id=transaction_id,
                customer_id=customer_id or None,
                items=order_items,
                total=total,
                status='confirmed'
            )

            # Link payment to order if exists
            customer_name = None
            customer_id_str = None
            try:
                payment = Payment.objects.filter(
                    transaction_id=transaction_id,
                    status='confirmed'
                ).latest('created_at')
                payment.order = order
                payment.save()
                customer_name = payment.mobile_number
                customer_id_str = payment.id
            except Payment.DoesNotExist:
                pass

            # Log activity
            log_activity(
                activity_type='booking',
                action=f'New order created: {order.order_id}',
                customer_id=customer_id_str or customer_id,
                customer_name=customer_name or 'Unknown',
                metadata={'order_id': order.order_id, 'total': float(total)}
            )

            # Clear cart after successful order creation (if customer_id was provided)
            if customer_id:
                try:
                    cart = Cart.objects.get(customer_id=customer_id)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass

            order_serializer = OrderSerializer(order)
            return JsonResponse({
                'success': True,
                'order': order_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancellationViewSet(viewsets.ViewSet):
    """ViewSet for cancellation operations matching API spec - admin only."""
    permission_classes = [IsAdmin]

    @action(detail=False, methods=['post'], url_path='submit')
    def submit_cancellation(self, request):
        """Submit cancellation request. POST /api/cancellations/submit"""
        try:
            serializer = SubmitCancellationSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            order_id = data['order_id']  # This is a string like "ORD123456"
            reason = data.get('reason', '')
            customer_phone = data.get('customer_phone', '')

            # Get order by order_id (string)
            try:
                order = Order.objects.get(order_id=order_id)
            except Order.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Create cancellation request
            cancellation = Cancellation.objects.create(
                order=order,
                customer_phone=customer_phone,
                reason=reason,
                cancellation_type='customer_request',
                status='pending'
            )

            # Log activity
            log_activity(
                activity_type='cancellation',
                action=f'Appointment cancelled: {order.order_id}',
                customer_id=cancellation.id,
                customer_name=customer_phone or 'Unknown',
                metadata={'order_id': order_id, 'reason': reason, 'cancellation_type': 'customer_request'}
            )

            return JsonResponse({
                'success': True,
                'request_id': cancellation.request_id,
                'message': 'Cancellation request submitted successfully',
                'customer_service_phone': '+92-300-1234567'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
