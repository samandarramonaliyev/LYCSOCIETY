from django.urls import path
from .views import MeetingListCreateAPIView, MeetingDetailAPIView, AnnouncementListCreateAPIView
urlpatterns=[path("clubs/<uuid:club_id>/meetings/",MeetingListCreateAPIView.as_view()),path("meetings/<uuid:meeting_id>/",MeetingDetailAPIView.as_view()),path("clubs/<uuid:club_id>/announcements/",AnnouncementListCreateAPIView.as_view())]
