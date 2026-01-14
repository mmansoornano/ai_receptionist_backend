"""Conversation history models."""
from django.db import models
from apps.core.models import Customer


class Conversation(models.Model):
    """Conversation history model."""
    CHANNEL_CHOICES = [
        ('voice', 'Voice Call'),
        ('sms', 'SMS'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='conversations', null=True, blank=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    phone_number = models.CharField(max_length=20)
    messages = models.JSONField(default=list)  # Store conversation messages
    intent = models.CharField(max_length=50, blank=True, null=True)
    conversation_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel} - {self.phone_number} - {self.created_at}"
