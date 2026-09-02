from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    # Represents one university/faculty using the platform.
    # Every other model (User, Lecturer, Hall, etc.) will eventually
    # carry a ForeignKey to this, to keep each tenant's data isolated.
    name = models.CharField(max_length=150)  # e.g. "Faculty of Information Technology"

    # Reserved for future subdomain-based tenant routing (e.g. "fit" -> fit.lectra.app).
    # Nullable because we don't need subdomains yet, just the column ready for later.
    domain_prefix = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  # set once, on insert

    def __str__(self):
        return self.name


class User(AbstractUser):
    # AbstractUser already gives us username, email, password, is_staff, etc.
    # We're extending it (not replacing it) to add role + tenant.

    class Role(models.TextChoices):
        # TextChoices = Django's enum for CharField choices.
        # Left side = value stored in the DB, right side = human-readable label
        # (shown in the admin site / forms).
        ADMIN = 'ADMIN', 'Admin'
        HOD = 'HOD', 'HOD / Coordinator'
        LECTURER = 'LECTURER', 'Lecturer'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT
    )

    # Which tenant (faculty/university) this user belongs to.
    # null=True/blank=True for now so existing rows / superuser creation
    # don't require picking a tenant immediately.
    # on_delete=CASCADE: if a Tenant is deleted, its users are deleted too.
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users',
    )

    def __str__(self):
        return f"{self.username} ({self.role})"