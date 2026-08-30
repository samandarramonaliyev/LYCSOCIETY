from django.urls import path
from .views import ReportCreateAPIView
urlpatterns=[path("reports/",ReportCreateAPIView.as_view())]
