import random
import re

from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from rest_framework import serializers

from .models import EmailOTP, User


# Only @uom.lk addresses are allowed to register — this regex is checked
# against whatever email the user types in, rejecting anything else
# (gmail.com, yahoo.com, etc.) before we even touch the database.
UOM_EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@uom\.lk$'


def generate_and_send_otp(uom_email):
    # random.randint is fine here since this OTP is short-lived and
    # single-use, not a long-term cryptographic secret — but worth
    # knowing: a production system handling something more sensitive
    # would typically reach for Python's `secrets` module instead of
    # `random`, since `random` isn't designed to be unpredictable in a
    # security sense (it's a statistical PRNG, not a cryptographic one).
    otp_code = str(random.randint(100000, 999999))

    EmailOTP.objects.create(uom_email=uom_email, otp_code=otp_code)

    # With EMAIL_BACKEND set to the console backend (see settings.py),
    # this doesn't actually email anyone — it prints the whole message
    # into your terminal where `runserver` is running. Look there for
    # the OTP code while testing.
    send_mail(
        subject='Your Lectra verification code',
        message=f'Your one-time verification code is: {otp_code}\n\nThis code expires in 10 minutes.',
        from_email='noreply@lectra.local',
        recipient_list=[uom_email],
    )


class RegisterSerializer(serializers.Serializer):
    # A plain Serializer (not ModelSerializer) on purpose: registration
    # takes a `password` field that doesn't map directly onto a real User
    # model field (passwords are never stored as raw text, only as a
    # hash), so ModelSerializer's automatic field-mapping would just get
    # in the way here rather than help.
    uom_email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)  # write_only: never echoed back in an API response

    def validate_uom_email(self, value):
        # DRF automatically calls any method named validate_<fieldname>
        # for that specific field, before create() ever runs.
        if not re.match(UOM_EMAIL_REGEX, value):
            raise serializers.ValidationError("Only @uom.lk email addresses are allowed.")
        return value

    def validate_password(self, value):
        # Reuses the AUTH_PASSWORD_VALIDATORS already configured in
        # settings.py (minimum length, not too common, not all-numeric,
        # etc.) instead of hand-writing our own password rules.
        validate_password(value)
        return value

    def create(self, validated_data):
        uom_email = validated_data['uom_email']
        username = validated_data['username']
        password = validated_data['password']

        # get_or_create so someone who registered but never entered their
        # OTP can just register again with the same email, rather than
        # being permanently locked out for abandoning the flow once.
        user, created = User.objects.get_or_create(
            uom_email=uom_email,
            defaults={'username': username},
        )

        if not created and user.is_uom_verified:
            # Only block if this email is BOTH already in the database
            # AND already fully verified — that's a genuine duplicate
            # signup attempt, not just someone retrying.
            raise serializers.ValidationError(
                {"uom_email": "This email is already registered and verified."}
            )

        # set_password() hashes the password before it's stored — Django
        # never keeps a raw, readable password anywhere, ever.
        user.set_password(password)
        user.username = username
        user.save()

        # Every registration attempt (fresh or retry) gets a brand new
        # OTP — this also doubles as a "resend code" mechanism for free.
        generate_and_send_otp(uom_email)

        return user
