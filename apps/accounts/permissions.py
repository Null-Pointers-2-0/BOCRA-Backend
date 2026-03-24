"""
Custom permission classes for the BOCRA Digital Platform.
"""
from rest_framework import permissions
from django.utils import timezone


class IsOwner(permissions.BasePermission):
    """
    Permission to only allow owners of an object to access it.
    
    Assumes the model instance has a 'user' attribute.
    Used for user-specific resources like profiles, applications, etc.
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the owner of the object.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: Model instance to check
            
        Returns:
            bool: True if user is owner, False otherwise
        """
        # Check if object has user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object is the user itself
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False


class IsStaff(permissions.BasePermission):
    """
    Permission to only allow staff users.
    
    Staff users can process applications and manage system data
    but cannot manage other users or system settings.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has staff permissions.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is staff, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_staff_member
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Check staff permission for object-level access.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: Model instance to check
            
        Returns:
            bool: True if user is staff, False otherwise
        """
        return self.has_permission(request, view)


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users.
    
    Admin users have full system access including user management
    and system configuration.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has admin permissions.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Check admin permission for object-level access.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: Model instance to check
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        return self.has_permission(request, view)


class IsCitizen(permissions.BasePermission):
    """
    Permission to only allow citizen users.
    
    Used for endpoints that should only be accessible by regular citizens,
    not staff or admin users.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has citizen role.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is citizen, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_citizen
        )


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Permission to allow owners or staff members.
    
    Commonly used for applications and complaints where:
    - Citizens can only access their own records
    - Staff can access all records for processing
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is owner or staff.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: Model instance to check
            
        Returns:
            bool: True if user is owner or staff, False otherwise
        """
        # Staff can access everything
        if request.user.is_staff_member:
            return True
        
        # Citizens can only access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow owners or admin users.
    
    More restrictive than IsOwnerOrStaff - only admins can access
    other users' data, not regular staff.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is owner or admin.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: Model instance to check
            
        Returns:
            bool: True if user is owner or admin, False otherwise
        """
        # Admin can access everything
        if request.user.is_admin:
            return True
        
        # Users can only access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsPublicOrAuthenticated(permissions.BasePermission):
    """
    Permission that allows public access for safe methods (GET, HEAD, OPTIONS)
    and requires authentication for unsafe methods.
    
    Used for public endpoints like publications and tenders where:
    - Anyone can view the data
    - Only authenticated users can create/modify data
    """
    
    def has_permission(self, request, view):
        """
        Check if request should be allowed based on method.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if request should be allowed, False otherwise
        """
        # Allow safe methods for public access
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication for unsafe methods
        return request.user and request.user.is_authenticated


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission to only allow users with verified email addresses.
    
    Used for sensitive operations that require email verification
    like submitting applications or filing complaints.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has verified email.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is verified, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.email_verified
        )


class IsNotLocked(permissions.BasePermission):
    """
    Permission to only allow users who are not locked.
    
    Prevents locked users from performing actions.
    """
    
    def has_permission(self, request, view):
        """
        Check if user account is not locked.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is not locked, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            not request.user.is_locked
        )


class CanProcessLicences(permissions.BasePermission):
    """
    Permission to allow users who can process licence applications.
    
    Staff and admin users can process licences.
    """
    
    def has_permission(self, request, view):
        """
        Check if user can process licences.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user can process licences, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.can_process_licences()
        )


class CanManageUsers(permissions.BasePermission):
    """
    Permission to allow users who can manage other users.
    
    Only admin users can manage users.
    """
    
    def has_permission(self, request, view):
        """
        Check if user can manage users.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user can manage users, False otherwise
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.can_manage_users()
        )


class IsSameUserOrAdmin(permissions.BasePermission):
    """
    Permission to allow users to access their own data or admin users.
    
    Used for user management endpoints where:
    - Users can access their own profile
    - Admins can access any user's profile
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is accessing their own data or is admin.
        
        Args:
            request: HTTP request object
            view: API view instance
            obj: User instance to check
            
        Returns:
            bool: True if access should be allowed, False otherwise
        """
        # Admin can access any user
        if request.user.is_admin:
            return True
        
        # Users can only access their own data
        return obj.id == request.user.id


class HasValidSubscription(permissions.BasePermission):
    """
    Permission to only allow users with valid subscriptions.
    
    For future use when implementing subscription-based features.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has valid subscription.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if user has valid subscription, False otherwise
        """
        # For now, all authenticated users have access
        # This can be extended to check subscription status
        return request.user and request.user.is_authenticated


class IsBusinessHours(permissions.BasePermission):
    """
    Permission to only allow access during business hours.
    
    Used for operations that should only be performed during
    BOCRA business hours (8 AM - 5 PM, Monday to Friday).
    """
    
    def has_permission(self, request, view):
        """
        Check if current time is during business hours.
        
        Args:
            request: HTTP request object
            view: API view instance
            
        Returns:
            bool: True if during business hours, False otherwise
        """
        now = timezone.now()
        
        # Check if it's weekday (Monday=0, Friday=4)
        if now.weekday() > 4:
            return False
        
        # Check if it's between 8 AM and 5 PM
        return 8 <= now.hour < 17
