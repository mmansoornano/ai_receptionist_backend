"""URLs for conversations app."""
from django.urls import path
from .views import ConversationListView

urlpatterns = [
    path('', ConversationListView.as_view(), name='conversation-list'),
]
