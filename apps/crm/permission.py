from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAthenticatedOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
class isOwnerOrReadOnly(BasePermission):

    def has_permission(self, request, view): 
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):

        if request.method in SAFE_METHODS:
            return True
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        if hasattr(obj, 'author'):
            return obj.author == request.user 
        if hasattr(obj, 'assigned_to'):
            return obj.assigned_to == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False
    
class IsStaffOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser
    
class IsCommentAuthor(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) 
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.author == request.user
    