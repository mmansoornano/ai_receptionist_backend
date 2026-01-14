"""Twilio webhook views."""
import sys
from pathlib import Path
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from django.conf import settings
from twilio.request_validator import RequestValidator
from .services import process_inbound_sms, process_inbound_call, process_voice_gather
import json
import os

# Add backend directory to Python path for utils import
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def validate_twilio_request(request):
    """Validate Twilio request signature."""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    url = request.build_absolute_uri()
    signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
    return validator.validate(url, request.POST, signature)


@csrf_exempt
@require_POST
def voice_webhook(request):
    """Handle inbound voice call webhook."""
    # For MVP, skip signature validation in development
    # In production, enable: if not validate_twilio_request(request): return HttpResponse('Unauthorized', status=403)
    
    from_number = request.POST.get('From', '')
    call_sid = request.POST.get('CallSid', '')
    
    # Process call
    call_data = process_inbound_call(from_number, call_sid)
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Greeting
    response.say(
        'Hello! Welcome to our reception. How can I help you today?',
        language='en-US'
    )
    
    # Gather speech input
    gather = Gather(
        input='speech',
        language='en-US',
        speech_timeout='auto',
        action='/webhooks/voice/gather',
        method='POST'
    )
    gather.say('How can I help you?', language='en-US')
    response.append(gather)
    
    # Fallback if no input
    response.say("I didn't hear anything. Please call again.", language='en-US')
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@require_POST
def voice_gather(request):
    """Handle voice input from Gather."""
    speech_result = request.POST.get('SpeechResult', '')
    conversation_id = request.POST.get('conversation_id', '')
    
    # If no conversation_id, try to get from call
    if not conversation_id:
        from_number = request.POST.get('From', '')
        from apps.conversations.models import Conversation
        try:
            conversation = Conversation.objects.filter(
                phone_number=from_number,
                channel='voice'
            ).latest('created_at')
            conversation_id = conversation.conversation_id
        except Conversation.DoesNotExist:
            pass
    
    # Process voice input
    result = process_voice_gather(conversation_id, speech_result)
    
    # Create TwiML response
    response = VoiceResponse()
    
    if 'say' in result:
        response.say(result['say'], language='en-US')
    
    if result.get('gather', False):
        gather = Gather(
            input='speech',
            language='en-US',
            speech_timeout='auto',
            action='/webhooks/voice/gather',
            method='POST'
        )
        if conversation_id:
            gather.action += f'?conversation_id={conversation_id}'
        response.append(gather)
    else:
        response.say('Thank you for calling. Goodbye!', language='en-US')
        response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@require_POST
def sms_webhook(request):
    """Handle inbound SMS webhook."""
    # For MVP, skip signature validation in development
    # In production, enable: if not validate_twilio_request(request): return HttpResponse('Unauthorized', status=403)
    
    from_number = request.POST.get('From', '')
    body = request.POST.get('Body', '')
    
    # Process SMS
    response_text = process_inbound_sms(from_number, body)
    
    # Create TwiML response
    response = MessagingResponse()
    response.message(response_text)
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_message(request):
    """Test endpoint for local development without Twilio.
    
    GET: Show test form
    POST: Process test message
    """
    from utils.logger import log_api_request, log_error
    
    if request.method == 'GET':
        return JsonResponse({
            'message': 'Send POST request with JSON: {"message": "your message", "phone": "+1234567890"}',
            'example': {
                'message': 'I want to book an appointment',
                'phone': '+1234567890'
            }
        })
    
    # POST request
    log_api_request("/webhooks/test-message/", "POST")
    
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        message = data.get('message', '')
        phone = data.get('phone', '+1234567890')
    else:
        # Form data
        message = request.POST.get('message', '')
        phone = request.POST.get('phone', '+1234567890')
    
    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)
    
    # Process message
    try:
        response_text = process_inbound_sms(phone, message)
        return JsonResponse({
            'success': True,
            'user_message': message,
            'agent_response': response_text,
            'message': response_text,  # Also include as 'message' for compatibility
            'phone': phone
        })
    except Exception as e:
        import traceback
        DEBUG = getattr(settings, 'DEBUG', False)
        log_error(e, "test_message endpoint")
        error_details = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        if DEBUG:
            error_details['traceback'] = traceback.format_exc()
        return JsonResponse(error_details, status=500)


@csrf_exempt
@require_POST
def call_status(request):
    """Handle call status callback."""
    # Log call status for debugging
    call_sid = request.POST.get('CallSid', '')
    status = request.POST.get('CallStatus', '')
    
    # You can store call status in database if needed
    # For MVP, just log it
    
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_POST
def text_to_speech(request):
    """Convert text to speech using Coqui TTS.
    
    Accepts text and returns audio WAV file.
    """
    from utils.logger import log_api_request, log_error
    
    log_api_request("/webhooks/tts/", "POST")
    
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            text = data.get('text', '')
        else:
            text = request.POST.get('text', '')
        
        if not text:
            return JsonResponse({'error': 'Text is required'}, status=400)
        
        # Import voice service
        from services.voice_service import VoiceService
        
        voice_service = VoiceService()
        audio_data = voice_service.text_to_speech(text)
        
        # Return audio as response
        response = HttpResponse(audio_data, content_type='audio/wav')
        response['Content-Disposition'] = 'inline; filename="speech.wav"'
        response['Content-Length'] = len(audio_data)
        
        log_api_request("/webhooks/tts/", "POST", {
            "text_length": len(text),
            "audio_size": len(audio_data)
        })
        
        return response
    except Exception as e:
        import traceback
        DEBUG = getattr(settings, 'DEBUG', False)
        log_error(e, "text_to_speech endpoint")
        
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        
        return JsonResponse({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc() if DEBUG else None
        }, status=500)


@csrf_exempt
@require_POST
def voice_transcribe(request):
    """Handle voice transcription for web chat.
    
    Accepts audio in various formats (WebM, Opus, WAV, MP3, etc.)
    Converts to optimal format for Whisper if needed.
    """
    from utils.logger import log_api_request, log_error
    
    log_api_request("/webhooks/voice/transcribe/", "POST", {
        "has_audio": 'audio' in request.FILES
    })
    
    if 'audio' not in request.FILES:
        return JsonResponse({'error': 'No audio file provided'}, status=400)
    
    audio_file = request.FILES['audio']
    phone = request.POST.get('phone', '+1234567890')
    
    # Determine file extension from content type or filename
    content_type = audio_file.content_type or ''
    filename = audio_file.name or 'audio'
    
    # Map content types to extensions
    extension_map = {
        'audio/webm': '.webm',
        'audio/opus': '.opus',
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/ogg': '.ogg',
    }
    
    # Get extension from content type or filename
    if content_type in extension_map:
        ext = extension_map[content_type]
    elif '.' in filename:
        ext = os.path.splitext(filename)[1]
    else:
        ext = '.webm'  # Default to webm (most common from MediaRecorder)
    
    tmp_path = None
    try:
        # Save temporary file with correct extension
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            for chunk in audio_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Use voice service for transcription
        from services.voice_service import VoiceService
        
        voice_service = VoiceService()
        transcribed_text = voice_service.speech_to_text(tmp_path)
        
        # Clean up
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return JsonResponse({
            'success': True,
            'text': transcribed_text
        })
    except Exception as e:
        import traceback
        DEBUG = getattr(settings, 'DEBUG', False)
        
        # Clean up on error
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
        
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        
        return JsonResponse({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc() if DEBUG else None
        }, status=500)
