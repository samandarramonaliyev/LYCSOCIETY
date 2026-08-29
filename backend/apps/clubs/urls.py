from django.urls import path

from .views import (
    ClubDetailAPIView,
    ClubListCreateAPIView,
    ClubModerationAPIView,
    ClubResubmitAPIView,
    JoinRequestActionAPIView,
    JoinRequestListCreateAPIView,
    LeaveClubAPIView,
    MemberListAPIView,
    MyClubAPIView,
)

app_name = "clubs"

urlpatterns = [
    path("clubs/", ClubListCreateAPIView.as_view(), name="club-list-create"),
    path("clubs/mine/", MyClubAPIView.as_view(), name="club-mine"),
    path("clubs/<uuid:club_id>/", ClubDetailAPIView.as_view(), name="club-detail"),
    path("clubs/<uuid:club_id>/resubmit/", ClubResubmitAPIView.as_view(), name="club-resubmit"),
    path("clubs/<uuid:club_id>/moderate/", ClubModerationAPIView.as_view(), name="club-moderate"),
    path("clubs/<uuid:club_id>/join-requests/", JoinRequestListCreateAPIView.as_view(), name="join-request-list-create"),
    path("clubs/<uuid:club_id>/members/", MemberListAPIView.as_view(), name="club-members"),
    path("clubs/<uuid:club_id>/leave/", LeaveClubAPIView.as_view(), name="club-leave"),
    path("join-requests/<uuid:request_id>/<str:action>/", JoinRequestActionAPIView.as_view(), name="join-request-action"),
]
