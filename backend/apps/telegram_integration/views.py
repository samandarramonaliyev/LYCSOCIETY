from __future__ import annotations

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent
from apps.common.throttling import TelegramInviteThrottle

from .client import TelegramBotClient
from .exceptions import TelegramAPIError
from .models import TelegramGroupStatus
from .services import create_member_invite, group_status, start_link, unlink_group


def _require_empty_body(request) -> None:  # type: ignore[no-untyped-def]
    if request.data:
        raise serializers.ValidationError("This action does not accept fields.")


class LinkStartAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        _require_empty_body(request)
        return Response({"token": start_link(club_id=club_id, user=request.user), "expires_in": 600})


class GroupStatusAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        group = group_status(club_id=club_id, user=request.user)
        return Response(
            {
                "linked": bool(group and group.status == TelegramGroupStatus.LINKED),
                "title": group.telegram_chat_title if group else "",
                "status": group.status if group else TelegramGroupStatus.UNLINKED,
                "linked_at": group.linked_at if group else None,
            }
        )

    def delete(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        _require_empty_body(request)
        unlink_group(club_id=club_id, user=request.user)
        return Response(status=204)


class InviteAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)
    throttle_classes = (TelegramInviteThrottle,)

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        _require_empty_body(request)
        try:
            link = create_member_invite(
                club_id=club_id,
                user=request.user,
                client=TelegramBotClient(),
            )
        except TelegramAPIError:
            return Response({"detail": "Telegram is temporarily unavailable."}, status=503)
        return Response({"invite_link": link})
