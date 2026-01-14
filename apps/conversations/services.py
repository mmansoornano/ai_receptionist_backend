"""Conversation management services."""
from .models import Conversation
from apps.core.models import Customer
from django.utils import timezone
import uuid


def get_or_create_conversation(phone_number: str, channel: str, customer=None) -> Conversation:
    """Get or create a conversation."""
    conversation_id = str(uuid.uuid4())
    conversation, created = Conversation.objects.get_or_create(
        phone_number=phone_number,
        channel=channel,
        defaults={
            'customer': customer,
            'conversation_id': conversation_id,
            'messages': [],
        }
    )
    if not created and not conversation.conversation_id:
        conversation.conversation_id = conversation_id
        conversation.save()
    return conversation


def add_message_to_conversation(conversation: Conversation, role: str, content: str):
    """Add a message to conversation history."""
    if not conversation.messages:
        conversation.messages = []
    conversation.messages.append({
        'role': role,
        'content': content,
        'timestamp': timezone.now().isoformat(),
    })
    conversation.save()


def update_conversation_intent(conversation: Conversation, intent: str):
    """Update conversation intent."""
    conversation.intent = intent
    conversation.save()
