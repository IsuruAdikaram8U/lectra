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

     # The verified university email — this becomes the user's real login
    # identity instead of Django's default `username` field. unique=True
    # means the database itself refuses two users with the same uom_email,
    # not just app-level validation.
    uom_email = models.EmailField(unique=True, db_index=True)

    # The personal Gmail address a user's Google account gets LINKED to,
    # once they connect "Sign in with Google" to their uom_email account.
    # null=True because most users won't have linked Google yet when their
    # row is first created — this gets filled in later, by a separate step.
    # unique=True still works fine with null=True in Postgres: multiple
    # rows can each have NULL here, Postgres only enforces uniqueness
    # between two *non-null* values.
    google_email = models.EmailField(null=True, blank=True, unique=True)

    # Google's own permanent internal ID for that Google account (a long
    # numeric string). We store this *in addition to* google_email because
    # emails can technically change on Google's side, but this ID never
    # does — it's the more reliable thing to match against on future logins.
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # False until the user has actually proved they own their uom_email
    # inbox (by entering the OTP we emailed them). Every login/permission
    # check should require this to be True — an unverified row means
    # someone typed an email address, not that they own it.
    is_uom_verified = models.BooleanField(default=False)

    # Tell Django's auth system: "log in with uom_email, not username."
    # This changes what field /api/token/ expects in its request body —
    # it becomes {"uom_email": ..., "password": ...} from now on.
    USERNAME_FIELD = 'uom_email'
    # Django's createsuperuser command still asks for these fields too,
    # on top of USERNAME_FIELD and password — username still exists as
    # an inherited AbstractUser field, so keep it required at creation time.
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.uom_email


class EmailOTP(models.Model):
    # A one-time-password row created every time we email someone a
    # verification code. Deliberately NOT a ForeignKey to User — during
    # signup, the OTP has to exist BEFORE a User row is created (we're
    # still verifying the email belongs to them), so there's nothing to
    # link to yet at that point. We just match on the raw email string.
    uom_email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    # Marked True the moment this OTP is successfully used, so the same
    # 6-digit code can't be replayed a second time by someone who saw it.
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # An OTP is only good for 10 minutes and only if nobody has
        # already used it. Both conditions must hold.
        from django.utils import timezone
        import datetime
        return not self.is_used and (timezone.now() - self.created_at) < datetime.timedelta(minutes=10)


    