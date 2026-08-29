from django.urls import path

from .views import HealthCheckAPIView

app_name = "common"

urlpatterns = [
    path("health/", HealthCheckAPIView.as_view(), name="health"),
]
