from django.urls import path

from .views import (
    CsrfTokenAPIView,
    CurrentAccountAPIView,
    LocalDevelopmentAuthenticationAPIView,
    LogoutAPIView,
    TelegramAuthenticationAPIView,
)

app_name = "identity"

urlpatterns = [
    path("csrf/", CsrfTokenAPIView.as_view(), name="csrf-token"),
    path("telegram/", TelegramAuthenticationAPIView.as_view(), name="telegram-authentication"),
    path("dev-login/", LocalDevelopmentAuthenticationAPIView.as_view(), name="local-development-authentication"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", CurrentAccountAPIView.as_view(), name="me"),
]
