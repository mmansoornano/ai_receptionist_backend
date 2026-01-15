"""URLs for authentication."""
from django.urls import path
from .views import login_view, get_current_user, logout_view

urlpatterns = [
    path('login/', login_view, name='auth-login'),
    path('me/', get_current_user, name='auth-me'),
    path('logout/', logout_view, name='auth-logout'),
]
