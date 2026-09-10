from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework import status

from accounts.models import EmailOTP, User
from accounts.permissions import IsAdmin
from accounts.serializers import RegisterSerializer



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


