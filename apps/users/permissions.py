from rest_framework import permissions
from apps.users.models import Role


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.SUPERADMIN)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == Role.SUPERADMIN or request.user.role == Role.ADMIN))


class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == Role.SUPERADMIN or request.user.role == Role.MANAGER))


class IsEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == Role.SUPERADMIN or request.user.role == Role.EMPLOYEE))


class IsAuditor(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == Role.SUPERADMIN or request.user.role == Role.AUDITOR))


class IsAccountant(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == Role.SUPERADMIN or request.user.role == Role.ACCOUNTANT))
