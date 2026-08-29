from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Meeting, Announcement
from .serializers import MeetingSerializer, AnnouncementSerializer
from .services import _club, create_meeting, create_announcement, accessible_meeting, cancel_meeting
class MeetingListCreateAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def get(self,r,club_id): return Response(MeetingSerializer(Meeting.objects.filter(club=_club(club_id,r.user)).order_by("starts_at"),many=True).data)
    def post(self,r,club_id): s=MeetingSerializer(data=r.data); s.is_valid(raise_exception=True); return Response(MeetingSerializer(create_meeting(club_id=club_id,user=r.user,data=s.validated_data)).data,status=201)
class MeetingDetailAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def get(self,r,meeting_id): return Response(MeetingSerializer(accessible_meeting(meeting_id,r.user)).data)
    def post(self,r,meeting_id): return Response(MeetingSerializer(cancel_meeting(meeting_id=meeting_id,user=r.user)).data)
class AnnouncementListCreateAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def get(self,r,club_id): return Response(AnnouncementSerializer(Announcement.objects.filter(club=_club(club_id,r.user)).order_by("-created_at"),many=True).data)
    def post(self,r,club_id): s=AnnouncementSerializer(data=r.data); s.is_valid(raise_exception=True); return Response(AnnouncementSerializer(create_announcement(club_id=club_id,user=r.user,data=s.validated_data)).data,status=201)
