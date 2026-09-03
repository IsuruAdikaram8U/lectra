"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import AdminOnlyPingView, CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT auth: POST username/password here to get access + refresh tokens
    # (with role/username/email embedded in the access token — see
    # accounts/views.py). POST the refresh token to the second URL to get
    # a new access token once the old one expires.
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Throwaway demo endpoint proving JWT auth + RBAC work — remove once
    # Phase 3 has real Admin-only endpoints to exercise instead.
    path('api/admin-ping/', AdminOnlyPingView.as_view(), name='admin_ping'),
]
