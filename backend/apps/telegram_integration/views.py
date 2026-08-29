from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models import ClubTelegramGroup
from .services import start_link, unlink_group, create_member_invite
from .client import TelegramBotClient
from .exceptions import TelegramAPIError

class LinkStartAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def post(self, request, club_id): return Response({"token":start_link(club_id=club_id,user=request.user),"expires_in":600})
class GroupStatusAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def get(self, request, club_id):
        g=ClubTelegramGroup.objects.filter(club_id=club_id, club__owner=request.user).first()
        return Response({"linked":bool(g and g.status=="LINKED"),"title":g.telegram_chat_title if g else "","status":g.status if g else "UNLINKED","linked_at":g.linked_at if g else None})
    def delete(self, request, club_id): unlink_group(club_id=club_id,user=request.user); return Response(status=204)
class InviteAPIView(APIView):
    permission_classes=(IsAuthenticated,)
    def post(self, request, club_id):
        try:
            link = create_member_invite(club_id=club_id,user=request.user,client=TelegramBotClient())
        except TelegramAPIError:
            return Response({"detail": "Telegram is temporarily unavailable."}, status=503)
        return Response({"invite_link": link})
