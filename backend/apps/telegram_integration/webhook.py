from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from apps.identity.models import User
from apps.lyceums.models import LyceumStatus, StudentRecord, StudentRecordStatus

from .client import TelegramBotClient
from .exceptions import LinkChallengeError, TelegramAPIError
from .models import ClubTelegramGroup, TelegramGroupStatus, TelegramWebhookUpdate
from .services import confirm_link


TELEGRAM_ALLOWED_UPDATES = ("message", "chat_join_request")
MAX_TELEGRAM_INTEGER = 9_223_372_036_854_775_807
CONNECT_COMMAND = re.compile(
    r"^/connect(?:@[A-Za-z0-9_]{1,64})?\s+([A-Za-z0-9_-]{20,128})$"
)


class MalformedTelegramUpdate(ValueError):
    """The transport JSON was valid, but did not contain a valid Update ID."""


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _telegram_id(value: object, *, positive: bool = False) -> int | None:
    if type(value) is not int or value == 0 or abs(value) > MAX_TELEGRAM_INTEGER:
        return None
    if positive and value < 0:
        return None
    return value


def _update_id(update: Mapping[str, Any]) -> int:
    value = _telegram_id(update.get("update_id"), positive=True)
    if value is None:
        raise MalformedTelegramUpdate
    return value


def _locked_delivery(update_id: int) -> TelegramWebhookUpdate:
    try:
        return TelegramWebhookUpdate.objects.select_for_update().get(update_id=update_id)
    except TelegramWebhookUpdate.DoesNotExist:
        try:
            with transaction.atomic():
                return TelegramWebhookUpdate.objects.create(update_id=update_id)
        except IntegrityError:
            return TelegramWebhookUpdate.objects.select_for_update().get(update_id=update_id)


def _handle_group_link(update: Mapping[str, Any], client: TelegramBotClient) -> None:
    message = _mapping(update.get("message"))
    if message is None:
        return
    text = message.get("text")
    chat = _mapping(message.get("chat"))
    sender = _mapping(message.get("from"))
    if not isinstance(text, str) or len(text) > 512 or chat is None or sender is None:
        return
    command = CONNECT_COMMAND.fullmatch(text.strip())
    if command is None:
        return

    chat_id = _telegram_id(chat.get("id"))
    owner_telegram_user_id = _telegram_id(sender.get("id"), positive=True)
    chat_type = chat.get("type")
    if (
        chat_id is None
        or owner_telegram_user_id is None
        or chat_type not in {"group", "supergroup"}
    ):
        return

    verified_chat = _mapping(client.get_chat(chat_id))
    bot = _mapping(client.get_me())
    if verified_chat is None or bot is None:
        return
    bot_id = _telegram_id(bot.get("id"), positive=True)
    if (
        bot_id is None
        or _telegram_id(verified_chat.get("id")) != chat_id
        or verified_chat.get("type") not in {"group", "supergroup"}
    ):
        return

    membership = _mapping(client.get_chat_member(chat_id, bot_id))
    member_user = _mapping(membership.get("user")) if membership else None
    if (
        membership is None
        or member_user is None
        or _telegram_id(member_user.get("id"), positive=True) != bot_id
        or membership.get("status") != "administrator"
        or membership.get("can_invite_users") is not True
    ):
        return

    try:
        confirm_link(
            token=command.group(1),
            telegram_chat_id=chat_id,
            title=verified_chat.get("title", ""),
            can_invite_members=True,
            # Group broadcasts are not an MVP behavior, so no unneeded messaging
            # capability is assumed or recorded during this access-control setup.
            can_send_messages=False,
            owner_telegram_user_id=owner_telegram_user_id,
        )
    except LinkChallengeError:
        # Invalid, expired, consumed, cross-owner, or duplicate challenges are permanent.
        return


def _has_current_membership(*, club: Club, user: User | None) -> bool:
    if user is None or not user.is_active or club.status != ClubStatus.ACTIVE:
        return False
    verified = StudentRecord.objects.select_for_update().filter(
        verified_user_id=user.pk,
        status=StudentRecordStatus.ACTIVE,
        lyceum__status=LyceumStatus.ACTIVE,
        lyceum_id=club.lyceum_id,
    ).exists()
    if not verified:
        return False
    return ClubMembership.objects.select_for_update().filter(
        club=club,
        user=user,
        status=MembershipStatus.ACTIVE,
    ).exists()


def _handle_join_request(update: Mapping[str, Any], client: TelegramBotClient) -> None:
    request = _mapping(update.get("chat_join_request"))
    if request is None:
        return
    chat = _mapping(request.get("chat"))
    sender = _mapping(request.get("from"))
    if chat is None or sender is None:
        return
    chat_id = _telegram_id(chat.get("id"))
    telegram_user_id = _telegram_id(sender.get("id"), positive=True)
    if chat_id is None or telegram_user_id is None:
        return

    initial_group = ClubTelegramGroup.objects.filter(
        telegram_chat_id=chat_id,
        status=TelegramGroupStatus.LINKED,
    ).values("pk", "club_id").first()
    if initial_group is None:
        # It is not a currently linked LYC Society group, so the bot takes no action.
        return

    user = User.objects.select_for_update().filter(
        telegram_user_id=telegram_user_id
    ).first()
    club = Club.objects.select_for_update().filter(pk=initial_group["club_id"]).first()
    group = ClubTelegramGroup.objects.select_for_update().filter(
        pk=initial_group["pk"],
        club=club,
        telegram_chat_id=chat_id,
        status=TelegramGroupStatus.LINKED,
    ).first()
    if club is None or group is None:
        return

    if _has_current_membership(club=club, user=user):
        client.approve_chat_join_request(chat_id, telegram_user_id)
    else:
        client.decline_chat_join_request(chat_id, telegram_user_id)


def _route_update(update: Mapping[str, Any], client: TelegramBotClient) -> None:
    if _mapping(update.get("message")) is not None:
        _handle_group_link(update, client)
    elif _mapping(update.get("chat_join_request")) is not None:
        _handle_join_request(update, client)


def process_telegram_webhook_update(
    *, update: Mapping[str, Any], client: TelegramBotClient
) -> bool:
    """Process one update once. Returns False when a prior delivery already completed."""

    update_id = _update_id(update)
    with transaction.atomic():
        delivery = _locked_delivery(update_id)
        if delivery.processed_at is not None:
            return False
        try:
            _route_update(update, client)
        except TelegramAPIError as exc:
            if exc.retryable:
                raise
            # Permanent provider errors cannot be made useful by Telegram retries.
        delivery.processed_at = timezone.now()
        delivery.save(update_fields=("processed_at", "updated_at"))
    return True
