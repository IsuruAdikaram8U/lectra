from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allows access only to users with role == ADMIN."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'ADMIN'
        )


class IsAdminOrHOD(BasePermission):
    """Allows access to ADMIN or HOD roles."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('ADMIN', 'HOD')
        )


class IsLecturer(BasePermission):
    """Allows access only to users with role == LECTURER."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'LECTURER'
        )


class IsStudent(BasePermission):
    """Allows access only to users with role == STUDENT."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'STUDENT'
        )


class IsAuthenticatedAnyRole(BasePermission):
    """
    Allows access to any logged-in user regardless of role — used for
    endpoints where the only requirement is "you must be logged in"
    (e.g. viewing your own profile), with no role restriction.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class BelongsToTenant(BasePermission):
    """
    Object-level permission: confirms the requesting user's tenant matches
    the tenant of the object they're trying to access. Use this alongside
    role-based permission classes (e.g. [IsAdmin, BelongsToTenant]) on any
    view that operates on tenant-scoped objects.

    Not wired into any real view yet — Phase 3's views (Module, Timetable,
    etc.) will use this once they exist. Exists now so it's ready to import.
    """
    def has_object_permission(self, request, view, obj):
        return getattr(obj, 'tenant_id', None) == request.user.tenant_id
