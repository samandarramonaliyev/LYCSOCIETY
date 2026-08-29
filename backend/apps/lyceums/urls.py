from django.urls import path

from .views import (
    VerificationClaimAPIView,
    VerificationLyceumListAPIView,
    VerificationStatusAPIView,
)

app_name = "lyceums"

urlpatterns = [
    path("lyceums/", VerificationLyceumListAPIView.as_view(), name="verification-lyceum-list"),
    path("status/", VerificationStatusAPIView.as_view(), name="verification-status"),
    path("claim/", VerificationClaimAPIView.as_view(), name="verification-claim"),
]
