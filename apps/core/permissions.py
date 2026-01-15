"""Custom permission classes for role-based access control."""
from rest_framework import permissions


class IsUser(permissions.BasePermission):
    """Allow access only to non-admin users (is_staff=False)."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated and is NOT an admin."""
        return (
            request.user and 
            request.user.is_authenticated and 
            not request.user.is_staff
        )


class IsAdmin(permissions.BasePermission):
    """Allow access only to admin users (is_staff=True)."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated and IS an admin."""
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_staff
        )


class IsUserOrAdmin(permissions.BasePermission):
    """Allow access to both users and admins (any authenticated user)."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated (either user or admin)."""
        return (
            request.user and 
            request.user.is_authenticated
        )
