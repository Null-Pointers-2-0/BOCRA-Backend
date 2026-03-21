from rest_framework.permissions import BasePermission

from .models import UserRole


class IsOwner(BasePermission):
    """Object-level: requester must be the owner of the resource."""

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == request.user
        return obj == request.user


class IsStaff(BasePermission):
    """Allow only BOCRA staff, admin, and superadmin roles."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN)
        )


class IsAdmin(BasePermission):
    """Allow only BOCRA admin and superadmin roles."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
        )


class IsCitizen(BasePermission):
    """Allow only the CITIZEN role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.CITIZEN
        )


class IsOwnerOrStaff(BasePermission):
    """Allow owners of a resource OR any staff/admin. Most common for applications."""

    def has_object_permission(self, request, view, obj):
        if request.user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return True
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == request.user
        return obj == request.user


class IsOwnerOrAdmin(BasePermission):
    """Stricter than IsOwnerOrStaff — requires Owner OR Admin (not plain Staff)."""

    def has_object_permission(self, request, view, obj):
        if request.user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            return True
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == request.user
        return obj == request.user


class IsPublicOrAuthenticated(BasePermission):
    """Safe methods (GET, HEAD, OPTIONS) are open; write requires authentication."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user and request.user.is_authenticated)


class IsVerifiedUser(BasePermission):
    """Require email_verified == True."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.email_verified
        )


class IsNotLocked(BasePermission):
    """Block requests from locked accounts."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and not request.user.is_locked
        )
