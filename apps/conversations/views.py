"""Views for conversations."""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import Conversation
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer, ConversationCreateSerializer
)
from apps.core.models import Customer
from apps.core.permissions import IsUser, IsUserOrAdmin
from apps.conversations.services import (
    get_or_create_conversation, add_message_to_conversation
)
from apps.webhooks.services import _call_agent_api


class ConversationViewSet(viewsets.ViewSet):
    """ViewSet for conversation operations - accessible to both users and admins."""
    permission_classes = [IsUserOrAdmin]  # Both users and admins can access
    
    def get_permissions(self):
        """Override permissions - all actions require IsUserOrAdmin permission."""
        return [IsUserOrAdmin()]
    
    def _is_admin_user(self, user):
        """Check if user is admin, staff, or superuser."""
        return user.is_staff or user.is_superuser
    
    def _get_user_customer_id(self, request):
        """Get customer ID for the authenticated user (user.id)."""
        try:
            # Try to get customer via OneToOneField first
            if hasattr(request.user, 'customer_profile'):
                return request.user.customer_profile.user.id if request.user.customer_profile.user else None
            # Fallback: find by email
            customer = Customer.objects.filter(email=request.user.email).first()
            if customer and customer.user:
                return customer.user.id
            # If customer exists but no user link, return user.id directly
            return request.user.id if request.user.is_authenticated else None
        except:
            return request.user.id if request.user.is_authenticated else None
    
    def _user_owns_conversation(self, request, conversation):
        """Check if the conversation belongs to the authenticated user.
        
        Uses user.id - conversation.customer.user.id must match request.user.id
        """
        if self._is_admin_user(request.user):
            return True  # Admins can access all
        
        user_id = request.user.id
        
        # Check if conversation's customer is linked to this user
        if conversation.customer and conversation.customer.user and conversation.customer.user.id == user_id:
            return True
        
        return False

    def list(self, request):
        """List conversations with filters. GET /api/conversations/ - Users see own, admins see all."""
        try:
            # Start with ordered queryset
            queryset = Conversation.objects.select_related('customer').order_by('-created_at')
            
            # If user is not admin/staff/superuser, filter to only their own conversations
            if not self._is_admin_user(request.user):
                user_id = request.user.id
                # Filter conversations where customer.user.id == user.id
                queryset = queryset.filter(customer__user__id=user_id)
            
            # Allow admins/staff/superusers to filter by customer_id if provided
            if self._is_admin_user(request.user):
                customer_id = request.GET.get('customer_id', '')
                if customer_id:
                    try:
                        if customer_id.startswith('customer_'):
                            customer_id_int = int(customer_id.split('_')[1])
                        else:
                            customer_id_int = int(customer_id)
                        queryset = queryset.filter(customer__id=customer_id_int)
                    except (ValueError, TypeError, IndexError):
                        pass

            # Search filter
            search = request.GET.get('search', '')
            if search:
                queryset = queryset.filter(
                    Q(customer__name__icontains=search) |
                    Q(customer__email__icontains=search) |
                    Q(phone_number__icontains=search)
                )

            # Status filter
            status_filter = request.GET.get('status', '')
            if status_filter:
                from datetime import timedelta
                if status_filter == 'active':
                    queryset = queryset.filter(
                        updated_at__gte=timezone.now() - timedelta(hours=24)
                    )
                elif status_filter == 'completed':
                    queryset = queryset.filter(
                        updated_at__lt=timezone.now() - timedelta(hours=24)
                    )
                elif status_filter == 'archived':
                    # Filter conversations with no messages
                    archived_ids = [c.id for c in queryset if not c.messages or len(c.messages) == 0]
                    queryset = queryset.filter(id__in=archived_ids)

            # Pagination
            try:
                page = int(request.GET.get('page', 1))
            except (ValueError, TypeError):
                page = 1
            
            try:
                page_size = int(request.GET.get('page_size', 20))
            except (ValueError, TypeError):
                page_size = 20
            
            # Ensure page_size is reasonable
            page_size = min(max(page_size, 1), 100)  # Between 1 and 100
            
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            conversations = queryset[start:end]

            serializer = ConversationListSerializer(conversations, many=True)

            # Build pagination URLs preserving all query parameters
            base_url = request.build_absolute_uri().split('?')[0]
            query_params = request.GET.copy()
            
            next_url = None
            if end < total:
                query_params['page'] = page + 1
                next_url = f"{base_url}?{query_params.urlencode()}"

            previous_url = None
            if page > 1:
                query_params['page'] = page - 1
                previous_url = f"{base_url}?{query_params.urlencode()}"

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

    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        """Get messages for a conversation. GET /api/conversations/{id}/messages/ - Users see own, admins see all."""
        try:
            # Convert pk to int
            try:
                pk_int = int(pk) if pk else None
            except (ValueError, TypeError):
                pk_int = None
            
            if pk_int is None:
                return JsonResponse({
                    'error': 'Invalid conversation ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get conversation
            try:
                conversation = Conversation.objects.get(id=pk_int)
            except Conversation.DoesNotExist:
                return JsonResponse({
                    'error': 'Conversation not found',
                    'message': f'No conversation found with ID {pk_int}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify user owns this conversation (or is admin)
            if not self._user_owns_conversation(request, conversation):
                return JsonResponse({
                    'error': 'Access denied',
                    'message': 'You do not have permission to access this conversation'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Format messages from JSONField
            messages = []
            if conversation.messages:
                for idx, msg in enumerate(conversation.messages):
                    messages.append({
                        'id': msg.get('id', idx + 1),
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', ''),
                        'timestamp': msg.get('timestamp', conversation.created_at.isoformat()),
                        'conversation_id': conversation.id
                    })
            
            return JsonResponse({'results': messages}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'error': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Get single conversation. GET /api/conversations/{id}/ - Users see own, admins see all."""
        try:
            # Convert pk to int if it's a string
            try:
                pk_int = int(pk) if pk else None
            except (ValueError, TypeError):
                pk_int = None
            
            if pk_int is None:
                return JsonResponse({
                    'error': 'Invalid conversation ID',
                    'message': f'Conversation ID must be a number, got: {pk}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get conversation
            try:
                conversation = Conversation.objects.select_related('customer').get(id=pk_int)
            except Conversation.DoesNotExist:
                return JsonResponse({
                    'error': 'Conversation not found',
                    'message': f'No conversation found with ID {pk_int}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify user owns this conversation (or is admin)
            if not self._user_owns_conversation(request, conversation):
                return JsonResponse({
                    'error': 'Access denied',
                    'message': 'You do not have permission to access this conversation'
                }, status=status.HTTP_403_FORBIDDEN)

            serializer = ConversationDetailSerializer(conversation)
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

    def create(self, request):
        """Create/update conversation and send message. POST /api/conversations/ - Users create own, admins can create any."""
        try:
            serializer = ConversationCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    'error': 'Validation error',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            customer_phone = data['customer_phone']
            message = data['message']
            customer_id = data.get('customer_id', '')
            customer_name = data.get('customer_name', '')
            customer_email = data.get('customer_email', '')

            # Determine which customer to use
            if self._is_admin_user(request.user):
                # Admin can create conversations for any customer
                # If customer_id is provided, use it; otherwise find/create by phone
                if customer_id:
                    try:
                        if isinstance(customer_id, str) and customer_id.startswith('customer_'):
                            customer_id_int = int(customer_id.split('_')[1])
                        else:
                            customer_id_int = int(customer_id)
                        customer = Customer.objects.get(id=customer_id_int)
                        # Update customer info if provided
                        updated = False
                        if customer_name and customer.name != customer_name:
                            customer.name = customer_name
                            updated = True
                        if customer_email and customer.email != customer_email:
                            customer.email = customer_email
                            updated = True
                        if customer_phone and customer.phone != customer_phone:
                            customer.phone = customer_phone
                            updated = True
                        if updated:
                            customer.save()
                    except (ValueError, Customer.DoesNotExist):
                        # Customer ID doesn't exist, create by phone
                        customer, _ = Customer.objects.get_or_create(
                            phone=customer_phone,
                            defaults={'name': customer_name or 'Unknown', 'email': customer_email}
                        )
                else:
                    # No customer_id, find/create by phone
                    customer, _ = Customer.objects.get_or_create(
                        phone=customer_phone,
                        defaults={'name': customer_name or 'Unknown', 'email': customer_email}
                    )
            else:
                # Regular user: always use their own customer record (linked to user)
                user = request.user
                try:
                    # Get or create customer linked to this user
                    customer, created = Customer.objects.get_or_create(
                        user=user,
                        defaults={
                            'name': customer_name or user.get_full_name() or user.username,
                            'email': customer_email or user.email,
                            'phone': customer_phone or f'user_{user.id}'
                        }
                    )
                    # Update customer info if provided
                    updated = False
                    if customer_name and customer.name != customer_name:
                        customer.name = customer_name
                        updated = True
                    if customer_email and customer.email != customer_email:
                        customer.email = customer_email
                        updated = True
                    if customer_phone and customer.phone != customer_phone:
                        customer.phone = customer_phone
                        updated = True
                    if updated:
                        customer.save()
                except Exception as e:
                    return JsonResponse({
                        'error': 'Access denied',
                        'message': f'Failed to get or create customer record: {str(e)}'
                    }, status=status.HTTP_403_FORBIDDEN)

            # Get or create conversation
            conversation = get_or_create_conversation(
                phone_number=customer_phone,
                channel='sms',  # Default to SMS for API
                customer=customer
            )

            # Log activity if this is a new conversation
            is_new_conversation = not conversation.messages or len(conversation.messages) == 0
            if is_new_conversation:
                from apps.core.models import log_activity
                log_activity(
                    activity_type='conversation',
                    action='New conversation started',
                    customer_id=customer.id if customer else None,
                    customer_name=customer_name or customer_phone,
                    metadata={'channel': 'sms', 'phone': customer_phone}
                )

            # Add user message
            add_message_to_conversation(conversation, 'user', message)

            # Call agent API
            try:
                agent_response = _call_agent_api(
                    message=message,
                    phone_number=customer_phone,
                    channel='sms',
                    conversation_id=conversation.conversation_id,
                    customer_id=str(customer.id) if customer else None
                )
                # Add agent response
                add_message_to_conversation(conversation, 'assistant', agent_response)
            except Exception as e:
                error_msg = f"Agent API error: {str(e)}"
                add_message_to_conversation(conversation, 'system', error_msg)
                agent_response = "I apologize, but a technical error occurred. Please try again later."

            # Return conversation with updated messages
            serializer = ConversationDetailSerializer(conversation)
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
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
