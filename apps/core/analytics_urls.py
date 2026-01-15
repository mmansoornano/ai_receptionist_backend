"""URLs for analytics."""
from django.urls import path
from .analytics_views import dashboard_stats, recent_activity

urlpatterns = [
    path('stats/', dashboard_stats, name='analytics-stats'),
    path('activity/', recent_activity, name='analytics-activity'),
]
