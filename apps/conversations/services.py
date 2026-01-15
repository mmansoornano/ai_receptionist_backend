"""Conversation management services."""
from .models import Conversation
from apps.core.models import Customer
from django.utils import timezone
import uuid


def get_or_create_conversation(phone_number: str, channel: str, customer=None) -> Conversation:
    """Get or create a conversation."""
    conversation_id = str(uuid.uuid4())
    # If customer is provided, try to find conversation by customer first, then by phone
    conversation = None
    if customer:
        try:
            # Try to find existing conversation for this customer and phone
            conversation = Conversation.objects.filter(
                customer=customer,
                phone_number=phone_number,
                channel=channel
            ).first()
        except Exception:
            pass
    
    if not conversation:
        # Fall back to original logic: find by phone and channel
        conversation, created = Conversation.objects.get_or_create(
            phone_number=phone_number,
            channel=channel,
            defaults={
                'customer': customer,
                'conversation_id': conversation_id,
                'messages': [],
            }
        )
        # If conversation exists but customer is different, update it
        if not created and customer and conversation.customer != customer:
            conversation.customer = customer
            conversation.save()
    
    if not conversation.conversation_id:
        conversation.conversation_id = conversation_id
        conversation.save()
    return conversation


def add_message_to_conversation(conversation: Conversation, role: str, content: str):
    """Add a message to conversation history."""
    if not conversation.messages:
        conversation.messages = []
    
    # Generate message ID
    message_id = len(conversation.messages) + 1
    
    conversation.messages.append({
        'id': message_id,
        'role': role,
        'content': content,
        'timestamp': timezone.now().isoformat(),
    })
    conversation.save()


def update_conversation_intent(conversation: Conversation, intent: str):
    """Update conversation intent."""
    conversation.intent = intent
    conversation.save()
