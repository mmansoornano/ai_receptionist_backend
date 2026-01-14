"""Twilio webhook processing services."""
import requests
import os
import sys
import time
from pathlib import Path
from django.conf import settings

# Add backend directory to Python path for utils import
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Note: Django is already set up when this module is imported
from apps.core.models import Customer
from apps.conversations.models import Conversation
from apps.conversations.services import (
    get_or_create_conversation,
    add_message_to_conversation,
    update_conversation_intent
)
from utils.logger import (
    backend_logger, log_api_request, log_agent_api_call, 
    log_agent_response, log_error
)

# Agent API URL - can be configured via environment variable
AGENT_API_URL = os.getenv('AGENT_API_URL', 'http://localhost:8001')


def _call_agent_api(message: str, phone_number: str, channel: str = 'sms', 
                   conversation_id: str = None, customer_id: str = None) -> str:
    """Call agent API endpoint."""
    start_time = time.time()
    
    log_agent_api_call(
        f"{AGENT_API_URL}/process",
        message,
    )
    
    try:
        response = requests.post(
            f"{AGENT_API_URL}/process",
            json={
                "message": message,
                "phone_number": phone_number,
                "channel": channel,
                "language": "en",
                "conversation_id": conversation_id,
                "customer_id": customer_id
            },
            timeout=30
        )
        response_time = time.time() - start_time
        
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            agent_response = data.get('response', '')
            log_agent_api_call(
                f"{AGENT_API_URL}/process",
                message,
                response_time
            )
            log_agent_response(agent_response, success=True)
            return agent_response
        else:
            error_msg = data.get('error', 'Unknown error from agent API')
            log_agent_response(error_msg, success=False)
            raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        response_time = time.time() - start_time
        log_agent_api_call(
            f"{AGENT_API_URL}/process",
            message,
            response_time
        )
        log_error(e, "Agent API Request")
        raise Exception(f"Agent API error: {str(e)}")


def process_inbound_sms(from_number: str, body: str) -> str:
    """Process inbound SMS message.
    
    Args:
        from_number: Sender phone number
        body: Message body
    
    Returns:
        Response message to send
    """
    backend_logger.info("=" * 80)
    log_api_request("SMS", "POST", {
        "from": from_number,
        "body": body[:100]
    })
    
    # Get or create customer
    customer, _ = Customer.objects.get_or_create(
        phone=from_number,
        defaults={'name': 'Unknown'}  # Will be updated by agent
    )
    
    # Get or create conversation
    conversation = get_or_create_conversation(
        phone_number=from_number,
        channel='sms',
        customer=customer
    )
    
    # Add user message to conversation
    add_message_to_conversation(conversation, 'user', body)
    
    # Process through agent API
    try:
        response = _call_agent_api(
            message=body,
            phone_number=from_number,
            channel='sms',
            conversation_id=conversation.conversation_id,
            customer_id=str(customer.id) if customer else None
        )
        
        # Add agent response to conversation
        add_message_to_conversation(conversation, 'assistant', response)
        
        return response
    
    except Exception as e:
        import traceback
        error_msg = f"An error occurred: {str(e)}"
        error_traceback = traceback.format_exc()
        print(f"Agent API Error: {error_msg}")
        print(f"Traceback: {error_traceback}")
        add_message_to_conversation(conversation, 'system', error_msg)
        return f"I apologize, but a technical error occurred: {str(e)}. Please try again later."


def process_inbound_call(from_number: str, call_sid: str) -> dict:
    """Process inbound call.
    
    Args:
        from_number: Caller phone number
        call_sid: Twilio call SID
    
    Returns:
        TwiML response dict
    """
    # Get or create customer
    customer, _ = Customer.objects.get_or_create(
        phone=from_number,
        defaults={'name': 'Unknown'}
    )
    
    # Get or create conversation
    conversation = get_or_create_conversation(
        phone_number=from_number,
        channel='voice',
        customer=customer
    )
    
    # For voice calls, we'll use Twilio's <Gather> to collect speech
    # The actual processing will happen in the status callback
    return {
        'action': f'/webhooks/voice/gather?conversation_id={conversation.conversation_id}',
        'method': 'POST',
        'language': 'en-US',
        'speech_timeout': 'auto',
    }


def process_voice_gather(conversation_id: str, speech_result: str = None) -> dict:
    """Process voice input from Twilio Gather.
    
    Args:
        conversation_id: Conversation ID
        speech_result: Transcribed speech text
    
    Returns:
        TwiML response dict
    """
    try:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
    except Conversation.DoesNotExist:
        return {'error': 'Conversation not found'}
    
    if not speech_result:
        # No speech detected, ask again
        return {
            'say': "I didn't hear what you said. Can you repeat?",
            'gather': True,
        }
    
    # Add user message
    add_message_to_conversation(conversation, 'user', speech_result)
    
    # Process through agent API
    try:
        response = _call_agent_api(
            message=speech_result,
            phone_number=conversation.phone_number,
            channel='voice',
            conversation_id=conversation_id,
            customer_id=str(conversation.customer.id) if conversation.customer else None
        )
        
        # Add agent response
        add_message_to_conversation(conversation, 'assistant', response)
        
        # Return TwiML response
        return {
            'say': response,
            'gather': True,  # Continue conversation
        }
    
    except Exception as e:
        error_msg = "I apologize, but a technical error occurred."
        return {
            'say': error_msg,
            'gather': True,
        }
