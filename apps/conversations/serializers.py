"""Serializers for conversations."""
from rest_framework import serializers
from .models import Conversation
from apps.core.serializers import CustomerSerializer


class ConversationSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'customer', 'channel', 'phone_number', 'messages',
            'intent', 'conversation_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
