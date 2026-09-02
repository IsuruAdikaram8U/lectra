from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    # Columns shown in the Tenant list page
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # UserAdmin is Django's built-in admin config for User models —
    # it already handles password hashing, permissions, etc. correctly.
    # We extend its fieldsets to also show our custom fields (role, tenant).
    fieldsets = UserAdmin.fieldsets + (
        ('Lectra info', {'fields': ('role', 'tenant')}),
    )
    list_display = ['username', 'email', 'role', 'tenant', 'is_staff']
