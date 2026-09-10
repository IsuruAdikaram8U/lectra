from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework import status

from accounts.models import EmailOTP, User
from accounts.permissions import IsAdmin
from accounts.serializers import RegisterSerializer
from django.conf import settings
from django.contrib.auth import authenticate
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed extra fields into the token payload itself, so the
        # frontend can read them by decoding the token — no extra
        # API call needed just to find out who's logged in.
        # NOTE: the JWT payload is signed, not encrypted — anyone holding
        # the token can read these values. Never put a password, OTP, or
        # anything else secret in here.
        token['role'] = user.role
        token['username'] = user.username
        # uom_email, not the legacy `email` field — this is the user's
        # real, verified identity now (see accounts/models.py).
        token['uom_email'] = user.uom_email
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    # Swaps in our serializer above so POST /api/token/ issues tokens
    # carrying role/username/email, instead of SimpleJWT's bare default.
    serializer_class = CustomTokenObtainPairSerializer


class AdminOnlyPingView(APIView):
    # Throwaway/demo endpoint proving JWT auth + RBAC work together end to
    # end, before Phase 3 builds real business endpoints on the same pattern.
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"message": f"Hello Admin {request.user.username}, you have access."})


class RegisterView(APIView):
    # Registration has to be reachable by someone who ISN'T logged in yet
    # at all — there's no token to check permissions against here, so we
    # explicitly clear DRF's default permission requirement.
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        # raise_exception=True: if validation fails (bad email domain,
        # weak password, etc.), DRF automatically turns that into a 400
        # response with the error details — we don't write that by hand.
        serializer.is_valid(raise_exception=True)
        serializer.save()  # runs RegisterSerializer.create() from serializers.py

        return Response(
            {"message": "Registration successful. Check the server console for your verification code."},
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    permission_classes = []  # same reasoning as RegisterView above

    def post(self, request):
        uom_email = request.data.get('uom_email')
        otp_code = request.data.get('otp_code')

        # Look up the MOST RECENT otp for this exact email+code pair.
        # Re-registering generates a fresh code every time, so there can
        # be several old EmailOTP rows lying around for the same email —
        # order_by('-created_at').first() grabs only the newest one.
        otp = (
            EmailOTP.objects
            .filter(uom_email=uom_email, otp_code=otp_code)
            .order_by('-created_at')
            .first()
        )

        if otp is None or not otp.is_valid():
            return Response(
                {"error": "Invalid or expired verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark it used immediately, so this exact code can never be
        # successfully replayed a second time.
        otp.is_used = True
        otp.save()

        user = User.objects.get(uom_email=uom_email)
        user.is_uom_verified = True
        user.save()

        # Verifying the OTP effectively IS the login — issue real JWT
        # tokens right here, so the frontend doesn't need a separate call
        # to /api/token/ immediately afterward.
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })


class GoogleAuthView(APIView):
    # "Sign in with Google" — the frontend gets an id_token straight from
    # Google's own Identity Services JS library and sends it here. We
    # never trust that token blindly: verify_oauth2_token cryptographically
    # checks Google's own signature on it, confirming it's real and
    # actually intended for OUR app (via the audience/client_id check).
    permission_classes = []

    def post(self, request):
        token = request.data.get('id_token')

        try:
            # audience=GOOGLE_CLIENT_ID: rejects a token that was issued
            # for a DIFFERENT Google app pretending to be ours — without
            # this check, any valid Google token from any app would pass.
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            # verify_oauth2_token raises ValueError for anything invalid —
            # expired, tampered with, wrong audience, malformed, etc.
            return Response(
                {"error": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 'sub' is Google's own permanent, unique ID for this Google
        # account — more reliable to match on than email (see the comment
        # on User.google_id in models.py for why).
        google_id = idinfo['sub']

        try:
            user = User.objects.get(google_id=google_id)
        except User.DoesNotExist:
            # This Google account has never been linked to a uom_email
            # account. Per the plan: tell the frontend so it can show the
            # "link your account" screen, rather than silently failing.
            return Response(
                {
                    "error": "ACCOUNT_NOT_LINKED",
                    "message": "No institution profile found for this Google account. Please verify with your university credentials to link.",
                    "google_email": idinfo.get('email'),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Known, already-linked Google account — log them straight in.
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })


class GoogleLinkView(APIView):
    # Links a Google account to an EXISTING uom_email account. Requires
    # proving ownership of BOTH: a fresh, valid Google id_token AND the
    # uom_email account's real password — linking two identities together
    # is exactly the kind of action that needs strong proof on both sides.
    permission_classes = []

    def post(self, request):
        token = request.data.get('id_token')
        uom_email = request.data.get('uom_email')
        password = request.data.get('password')

        try:
            # Re-verify the Google token here too — never trust a
            # google_id/email the client just tells you directly in the
            # request body, always re-derive it from a freshly verified token.
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response(
                {"error": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # authenticate() checks uom_email + password against the database,
        # the same way logging in normally does. Passing it as `username`
        # works even though our real field is uom_email — Django's
        # ModelBackend specifically supports this for custom USERNAME_FIELD
        # models, falling back to the literal `username` kwarg.
        user = authenticate(request, username=uom_email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid university email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Credentials proven — now actually link the two identities together.
        user.google_id = idinfo['sub']
        user.google_email = idinfo.get('email')
        user.save()

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })
