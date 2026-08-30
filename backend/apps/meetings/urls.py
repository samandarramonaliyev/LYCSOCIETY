from django.urls import path

from .views import (
    AnnouncementListCreateAPIView,
    MeetingDetailAPIView,
    MeetingListCreateAPIView,
    RSVPAPIView,
)

app_name = "meetings"

urlpatterns = [
    path("clubs/<uuid:club_id>/meetings/", MeetingListCreateAPIView.as_view()),
    path("meetings/<uuid:meeting_id>/", MeetingDetailAPIView.as_view()),
    path("meetings/<uuid:meeting_id>/rsvp/", RSVPAPIView.as_view()),
    path("clubs/<uuid:club_id>/announcements/", AnnouncementListCreateAPIView.as_view()),
]
