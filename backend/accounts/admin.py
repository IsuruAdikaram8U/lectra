from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    # Columns shown in the Tenant list page
    list_display = ['name', 'domain_prefix', 'created_at']
    search_fields = ['name']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # UserAdmin is Django's built-in admin config for User models —
    # it already handles password hashing, permissions, etc. correctly.
    # We extend its fieldsets to also show our custom fields.
    fieldsets = UserAdmin.fieldsets + (
        ('Lectra info', {'fields': ('role', 'tenant')}),
        # New dual-auth fields from the Google-linking flow — shown as
        # their own section so they're editable/visible in the admin,
        # separate from Django's built-in auth fields above.
        ('University identity', {'fields': ('uom_email', 'is_uom_verified')}),
        ('Linked Google account', {'fields': ('google_email', 'google_id')}),
    )
    # uom_email replaces email here — it's the field that actually
    # matters now (the real login identity), the inherited `email`
    # field is unused/legacy at this point.
    list_display = ['username', 'uom_email', 'google_email', 'role', 'tenant', 'is_staff']


