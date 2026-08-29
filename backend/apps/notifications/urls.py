from django.urls import path
from .views import NotificationListAPIView, NotificationReadAPIView, PreferenceAPIView
urlpatterns = [path("notifications/", NotificationListAPIView.as_view()), path("notifications/<uuid:notification_id>/read/", NotificationReadAPIView.as_view()), path("notification-preferences/", PreferenceAPIView.as_view())]
