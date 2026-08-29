from django.urls import path

from .views import VerificationClaimAPIView, VerificationStatusAPIView

app_name = "lyceums"

urlpatterns = [
    path("status/", VerificationStatusAPIView.as_view(), name="verification-status"),
    path("claim/", VerificationClaimAPIView.as_view(), name="verification-claim"),
]
