"""URLs for webhooks app."""
from django.urls import path
from .views import voice_webhook, voice_gather, sms_webhook, call_status, test_message, voice_transcribe, text_to_speech

urlpatterns = [
    path('voice/', voice_webhook, name='voice-webhook'),
    path('voice/gather', voice_gather, name='voice-gather'),
    path('voice/transcribe/', voice_transcribe, name='voice-transcribe'),
    path('tts/', text_to_speech, name='text-to-speech'),
    path('sms/', sms_webhook, name='sms-webhook'),
    path('call-status/', call_status, name='call-status'),
    path('test-message/', test_message, name='test-message'),  # For local testing without Twilio
]
