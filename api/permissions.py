# api/permissions.py

from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit"""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owner
        return obj.user == request.user or obj.author == request.user


class IsCelebrityUser(permissions.BasePermission):
    """Only celebrity users can access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'celebrity'


class IsFanUser(permissions.BasePermission):
    """Only fan users can access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'fan'


class IsAdminOrSubAdmin(permissions.BasePermission):
    """Only admin or sub-admin can access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['admin', 'subadmin']