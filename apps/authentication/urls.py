"""URLs for authentication."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import login_view, get_current_user, logout_view, signup_view, create_superuser

urlpatterns = [
    path('login/', login_view, name='auth-login'),
    path('signup/', signup_view, name='auth-signup'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', get_current_user, name='auth-me'),
    path('logout/', logout_view, name='auth-logout'),
    path('create-superuser/', create_superuser, name='auth-create-superuser'),
]
