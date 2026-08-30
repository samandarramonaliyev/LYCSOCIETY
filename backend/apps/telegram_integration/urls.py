from django.urls import path
from .views import (
    GroupStatusAPIView,
    InviteAPIView,
    LinkStartAPIView,
    TelegramWebhookAPIView,
)

urlpatterns = [
    path("clubs/<uuid:club_id>/telegram/link/start/", LinkStartAPIView.as_view()),
    path("clubs/<uuid:club_id>/telegram/", GroupStatusAPIView.as_view()),
    path("clubs/<uuid:club_id>/telegram/invite/", InviteAPIView.as_view()),
    path("telegram/webhook/", TelegramWebhookAPIView.as_view()),
]
