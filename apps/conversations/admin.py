"""Django admin for conversations."""
from django.contrib import admin
from .models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'channel', 'intent', 'customer', 'created_at']
    list_filter = ['channel', 'intent', 'created_at']
    search_fields = ['phone_number', 'conversation_id']
    readonly_fields = ['created_at', 'updated_at', 'messages']
