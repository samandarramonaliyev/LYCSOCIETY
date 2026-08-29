from django.urls import path
from .views import LinkStartAPIView, GroupStatusAPIView, InviteAPIView
urlpatterns=[path("clubs/<uuid:club_id>/telegram/link/start/",LinkStartAPIView.as_view()),path("clubs/<uuid:club_id>/telegram/",GroupStatusAPIView.as_view()),path("clubs/<uuid:club_id>/telegram/invite/",InviteAPIView.as_view())]
