from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.permissions import IsAdmin


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
        token['email'] = user.email
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
