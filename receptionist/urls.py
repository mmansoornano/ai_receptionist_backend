"""receptionist URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/conversations/', include('apps.conversations.urls')),
    path('api/analytics/', include('apps.core.analytics_urls')),
    path('webhooks/', include('apps.webhooks.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
