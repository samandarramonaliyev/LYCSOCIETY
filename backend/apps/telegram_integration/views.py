from __future__ import annotations

import hmac
import json
import logging

from django.conf import settings
from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent
from apps.common.throttling import TelegramInviteThrottle

from .client import TelegramBotClient
from .exceptions import TelegramAPIError
from .models import TelegramGroupStatus
from .services import create_member_invite, group_status, start_link, unlink_group
from .webhook import MalformedTelegramUpdate, process_telegram_webhook_update


logger = logging.getLogger(__name__)


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


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookAPIView(APIView):
    """Telegram's server-to-server endpoint; it never uses a student session."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = ()
    http_method_names = ("post",)
    max_body_bytes = 262_144

    def post(self, request: HttpRequest) -> Response:
        if not settings.TELEGRAM_WEBHOOK_ENABLED:
            return Response({"detail": "Not found."}, status=404)
        supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        try:
            valid_secret = hmac.compare_digest(
                settings.TELEGRAM_WEBHOOK_SECRET.encode("ascii"),
                supplied_secret.encode("ascii"),
            )
        except UnicodeEncodeError:
            valid_secret = False
        if not supplied_secret or not valid_secret:
            return Response({"detail": "Invalid request."}, status=403)
        if len(request.body) > self.max_body_bytes:
            return Response({"detail": "Invalid request."}, status=400)
        try:
            update = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response({"detail": "Invalid request."}, status=400)
        if not isinstance(update, dict):
            return Response({"detail": "Invalid request."}, status=400)
        try:
            process_telegram_webhook_update(update=update, client=TelegramBotClient())
        except MalformedTelegramUpdate:
            return Response({"detail": "Invalid request."}, status=400)
        except TelegramAPIError as exc:
            # Retryable errors deliberately receive non-2xx; no provider text is exposed.
            logger.warning(
                "Telegram webhook provider failure",
                extra={"exception_type": type(exc).__name__},
            )
            return Response({"detail": "Temporary processing failure."}, status=503)
        except Exception as exc:
            logger.error(
                "Telegram webhook processing failure",
                extra={"exception_type": type(exc).__name__},
            )
            return Response({"detail": "Temporary processing failure."}, status=503)
        return Response(status=204)
