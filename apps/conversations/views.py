"""Views for conversations."""
from rest_framework import generics
from rest_framework.response import Response
from .models import Conversation
from .serializers import ConversationSerializer


class ConversationListView(generics.ListAPIView):
    """List conversations."""
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
