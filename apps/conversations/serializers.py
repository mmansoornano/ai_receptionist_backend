"""Serializers for conversations."""
from rest_framework import serializers
from .models import Conversation
from apps.core.serializers import CustomerSerializer


class MessageSerializer(serializers.Serializer):
    """Serializer for individual messages."""
    id = serializers.IntegerField(required=False)
    role = serializers.CharField()
    content = serializers.CharField()
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """Get timestamp from message dict or use current time."""
        if isinstance(obj, dict):
            # Handle dict format from JSONField
            timestamp_str = obj.get('timestamp')
            if timestamp_str:
                try:
                    from django.utils.dateparse import parse_datetime
                    return parse_datetime(timestamp_str)
                except:
                    from django.utils import timezone
                    return timezone.now()
        elif hasattr(obj, 'timestamp'):
            return obj.timestamp
        from django.utils import timezone
        return timezone.now()


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list (summary)."""
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_id', 'customer_name', 'customer_email', 'customer_phone',
            'last_message', 'last_message_time', 'message_count', 'status', 'intent',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_id(self, obj):
        """Get customer ID as number."""
        if obj.customer:
            return obj.customer.id if obj.customer.id else None
        return None

    def _get_user_from_customer_email(self, obj):
        """Helper to get User from customer email."""
        if obj.customer and obj.customer.email:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                return User.objects.filter(email=obj.customer.email).first()
            except (ValueError, AttributeError):
                pass
        return None

    def get_customer_name(self, obj):
        """Get customer name."""
        # First try from Customer model
        if obj.customer and obj.customer.name and obj.customer.name != 'Unknown':
            return obj.customer.name
        
        # Try to fetch from User model using customer email
        user = self._get_user_from_customer_email(obj)
        if user:
            name = user.get_full_name() or user.first_name or user.username
            if name and name.strip():
                # Update Customer record if it exists
                if obj.customer:
                    obj.customer.name = name
                    obj.customer.save(update_fields=['name'])
                return name
        
        # Fallback to Customer model or None
        return obj.customer.name if obj.customer else None

    def get_customer_email(self, obj):
        """Get customer email."""
        # First try from Customer model
        if obj.customer and obj.customer.email:
            return obj.customer.email
        
        # Try to fetch from User model using customer email
        user = self._get_user_from_customer_email(obj)
        if user and user.email:
            # Update Customer record if it exists
            if obj.customer:
                obj.customer.email = user.email
                obj.customer.save(update_fields=['email'])
            return user.email
        
        # Fallback to Customer model or None
        return obj.customer.email if obj.customer else None

    def get_customer_phone(self, obj):
        """Get customer phone."""
        return obj.phone_number

    def get_last_message(self, obj):
        """Get last message content."""
        if obj.messages and len(obj.messages) > 0:
            last_msg = obj.messages[-1]
            return last_msg.get('content', '')
        return ''

    def get_last_message_time(self, obj):
        """Get last message timestamp."""
        if obj.messages and len(obj.messages) > 0:
            last_msg = obj.messages[-1]
            timestamp = last_msg.get('timestamp')
            if timestamp:
                # If it's already a datetime object, return it
                if hasattr(timestamp, 'isoformat'):
                    return timestamp
                # If it's a string, try to parse it
                try:
                    from django.utils.dateparse import parse_datetime
                    parsed = parse_datetime(str(timestamp))
                    if parsed:
                        return parsed
                except:
                    pass
            # Fallback to updated_at
            return obj.updated_at
        return obj.updated_at

    def get_message_count(self, obj):
        """Get message count."""
        return len(obj.messages) if obj.messages else 0

    def get_status(self, obj):
        """Get conversation status."""
        # Determine status based on last activity
        if not obj.messages or len(obj.messages) == 0:
            return 'archived'
        # Consider active if updated in last 24 hours
        from django.utils import timezone
        from datetime import timedelta
        if obj.updated_at > timezone.now() - timedelta(hours=24):
            return 'active'
        return 'completed'


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for single conversation with messages."""
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    
    def get_messages(self, obj):
        """Get messages from JSONField and format them."""
        if not obj.messages:
            return []
        
        formatted_messages = []
        for idx, msg in enumerate(obj.messages):
            formatted_messages.append({
                'id': msg.get('id', idx + 1),
                'role': msg.get('role', 'user'),
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp', obj.created_at.isoformat() if hasattr(obj, 'created_at') else None)
            })
        
        return formatted_messages

    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_id', 'customer_name', 'customer_email', 'customer_phone',
            'status', 'intent', 'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_id(self, obj):
        """Get customer ID as number."""
        if obj.customer:
            return obj.customer.id if obj.customer.id else None
        return None

    def _get_user_from_customer_email(self, obj):
        """Helper to get User from customer email."""
        if obj.customer and obj.customer.email:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                return User.objects.filter(email=obj.customer.email).first()
            except (ValueError, AttributeError):
                pass
        return None

    def get_customer_name(self, obj):
        """Get customer name."""
        # First try from Customer model
        if obj.customer and obj.customer.name and obj.customer.name != 'Unknown':
            return obj.customer.name
        
        # Try to fetch from User model using customer email
        user = self._get_user_from_customer_email(obj)
        if user:
            name = user.get_full_name() or user.first_name or user.username
            if name and name.strip():
                # Update Customer record if it exists
                if obj.customer:
                    obj.customer.name = name
                    obj.customer.save(update_fields=['name'])
                return name
        
        # Fallback to Customer model or None
        return obj.customer.name if obj.customer else None

    def get_customer_email(self, obj):
        """Get customer email."""
        # First try from Customer model
        if obj.customer and obj.customer.email:
            return obj.customer.email
        
        # Try to fetch from User model using customer email
        user = self._get_user_from_customer_email(obj)
        if user and user.email:
            # Update Customer record if it exists
            if obj.customer:
                obj.customer.email = user.email
                obj.customer.save(update_fields=['email'])
            return user.email
        
        # Fallback to Customer model or None
        return obj.customer.email if obj.customer else None

    def get_customer_phone(self, obj):
        """Get customer phone."""
        return obj.phone_number

    def get_status(self, obj):
        """Get conversation status."""
        from django.utils import timezone
        from datetime import timedelta
        if not obj.messages or len(obj.messages) == 0:
            return 'archived'
        if obj.updated_at > timezone.now() - timedelta(hours=24):
            return 'active'
        return 'completed'


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating conversation."""
    customer_id = serializers.CharField(required=False, allow_blank=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    user_id = serializers.IntegerField(required=False)
