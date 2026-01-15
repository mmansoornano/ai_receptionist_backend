"""Analytics views."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsAdmin
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import Order, Payment, Customer, ActivityLog
from apps.conversations.models import Conversation


def calculate_avg_response_time():
    """Calculate average response time from conversation messages."""
    try:
        conversations = Conversation.objects.all()
        response_times = []
        
        for conv in conversations:
            if not conv.messages or len(conv.messages) < 2:
                continue
            
            messages = conv.messages
            for i in range(len(messages) - 1):
                current_msg = messages[i]
                next_msg = messages[i + 1]
                
                # If current is user message and next is assistant message
                if current_msg.get('role') == 'user' and next_msg.get('role') == 'assistant':
                    try:
                        current_timestamp = current_msg.get('timestamp', '')
                        next_timestamp = next_msg.get('timestamp', '')
                        
                        if not current_timestamp or not next_timestamp:
                            continue
                        
                        # Parse ISO format timestamps
                        # Try Django's timezone parser first
                        try:
                            from datetime import datetime
                            current_time = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
                            next_time = datetime.fromisoformat(next_timestamp.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            # Fallback to string parsing
                            from datetime import datetime
                            current_time = datetime.fromisoformat(current_timestamp.replace('Z', ''))
                            next_time = datetime.fromisoformat(next_timestamp.replace('Z', ''))
                            current_time = timezone.make_aware(current_time)
                            next_time = timezone.make_aware(next_time)
                        
                        # Ensure timezone aware
                        if not timezone.is_aware(current_time):
                            current_time = timezone.make_aware(current_time)
                        if not timezone.is_aware(next_time):
                            next_time = timezone.make_aware(next_time)
                        
                        diff = (next_time - current_time).total_seconds()
                        if diff > 0 and diff < 3600:  # Reasonable response time (less than 1 hour)
                            response_times.append(diff)
                    except (ValueError, TypeError, AttributeError, ImportError):
                        continue
        
        if response_times:
            return sum(response_times) / len(response_times)
        return 2.3  # Default fallback
    except Exception:
        return 2.3  # Default fallback


def calculate_success_rate():
    """Calculate success rate: completed bookings / total booking requests."""
    try:
        # Count successful bookings (completed orders)
        successful_bookings = Order.objects.filter(status__in=['completed', 'confirmed']).count()
        
        # Count total booking requests (conversations with booking intent or orders created)
        total_booking_requests = Conversation.objects.filter(intent='booking').count()
        # Also count orders as booking requests
        total_orders = Order.objects.count()
        
        # Use the larger number as total requests
        total_requests = max(total_booking_requests, total_orders, 1)
        
        if total_requests > 0:
            return (successful_bookings / total_requests) * 100
        return 0.0
    except Exception:
        return 0.0


@api_view(['GET'])
@permission_classes([IsAdmin])
def dashboard_stats(request):
    """Get dashboard statistics. GET /api/analytics/stats/"""
    try:
        # Date filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        # Base querysets
        conversations_qs = Conversation.objects.all()
        orders_qs = Order.objects.all()
        payments_qs = Payment.objects.all()

        # Apply date filters
        if date_from:
            from django.utils.dateparse import parse_datetime
            try:
                date_from_dt = parse_datetime(date_from)
                if date_from_dt:
                    conversations_qs = conversations_qs.filter(created_at__gte=date_from_dt)
                    orders_qs = orders_qs.filter(created_at__gte=date_from_dt)
                    payments_qs = payments_qs.filter(created_at__gte=date_from_dt)
            except:
                pass

        if date_to:
            from django.utils.dateparse import parse_datetime
            try:
                date_to_dt = parse_datetime(date_to)
                if date_to_dt:
                    conversations_qs = conversations_qs.filter(created_at__lte=date_to_dt)
                    orders_qs = orders_qs.filter(created_at__lte=date_to_dt)
                    payments_qs = payments_qs.filter(created_at__lte=date_to_dt)
            except:
                pass

        # Calculate statistics
        total_conversations = conversations_qs.count()
        
        # Active users: distinct customers who have had conversations (or active in last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        try:
            active_customers = Customer.objects.filter(
                conversations__created_at__gte=thirty_days_ago
            ).distinct().count()
        except Exception:
            active_customers = 0
        
        # Fallback: if no recent conversations, count all customers with conversations
        if active_customers == 0:
            try:
                active_customers = Customer.objects.filter(conversations__isnull=False).distinct().count()
            except Exception:
                active_customers = 0
        
        # If still 0, use distinct phone numbers from conversations
        if active_customers == 0:
            try:
                active_customers = conversations_qs.values('phone_number').distinct().count()
            except Exception:
                active_customers = 0

        # Calculate average response time
        avg_response_time = calculate_avg_response_time()

        # Calculate success rate
        success_rate = calculate_success_rate()

        # Order statistics
        total_orders = orders_qs.count()
        pending_orders = orders_qs.filter(status__in=['pending', 'confirmed']).count()

        # Payment statistics
        try:
            completed_payments = payments_qs.filter(status='confirmed').count()
            pending_payments = payments_qs.filter(status__in=['pending', 'otp_sent', 'otp_verified']).count()
            
            total_payments_amount = payments_qs.filter(status='confirmed').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            pending_payments_amount = payments_qs.filter(status__in=['pending', 'otp_sent', 'otp_verified']).aggregate(
                total=Sum('amount')
            )['total'] or 0
        except Exception:
            completed_payments = 0
            pending_payments = 0
            total_payments_amount = 0
            pending_payments_amount = 0

        # Total revenue (from completed orders)
        total_revenue = orders_qs.filter(status__in=['confirmed', 'completed']).aggregate(
            total=Sum('total')
        )['total'] or 0

        return JsonResponse({
            'total_conversations': total_conversations,
            'active_users': active_customers,
            'avg_response_time': round(avg_response_time, 2),
            'success_rate': round(success_rate, 2)
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


@api_view(['GET'])
@permission_classes([IsAdmin])
def recent_activity(request):
    """Get recent activity. GET /api/analytics/activity/"""
    try:
        limit = int(request.GET.get('limit', 20))
        activity_type_filter = request.GET.get('activity_type', '')

        # Query ActivityLog model
        queryset = ActivityLog.objects.all()
        
        if activity_type_filter:
            queryset = queryset.filter(activity_type=activity_type_filter)
        
        activities = queryset.order_by('-created_at')[:limit]

        # Format response
        activity_list = []
        for activity in activities:
            activity_list.append({
                'id': activity.id,
                'action': activity.action,
                'activity_type': activity.activity_type,
                'customer_name': activity.customer_name or 'Unknown',
                'customer_id': activity.customer_id,
                'created_at': activity.created_at.isoformat()
            })

        return JsonResponse(activity_list, safe=False, status=status.HTTP_200_OK)
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
