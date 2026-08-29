from django.urls import path

from .views import InterestListAPIView, ProfileAPIView

app_name = "profiles"

urlpatterns = [
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path("interests/", InterestListAPIView.as_view(), name="interests"),
]
