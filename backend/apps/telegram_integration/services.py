from __future__ import annotations

from datetime import timedelta
import hashlib
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from apps.identity.models import User
from apps.lyceums.services.scoping import get_verified_lyceum

from .exceptions import LinkChallengeError
from .models import ClubTelegramGroup, TelegramGroupStatus, TelegramLinkChallenge


@transaction.atomic
def start_link(*, club_id, user) -> str:  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    club = Club.objects.select_for_update().filter(
        pk=club_id,
        owner=user,
        lyceum=lyceum,
        status=ClubStatus.ACTIVE,
    ).first()
    if club is None:
        raise NotFound("Club not found.")
    token = secrets.token_urlsafe(32)
    TelegramLinkChallenge.objects.filter(
        club=club,
        used_at__isnull=True,
    ).update(used_at=timezone.now())
    TelegramLinkChallenge.objects.create(
        club=club,
        expected_owner=user,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return token


@transaction.atomic
def confirm_link(
    *,
    token,
    telegram_chat_id,
    title="",
    can_invite_members=False,
    can_send_messages=False,
    owner_telegram_user_id=None,
):  # type: ignore[no-untyped-def]
    if (
        type(telegram_chat_id) is not int
        or telegram_chat_id == 0
        or type(owner_telegram_user_id) is not int
        or owner_telegram_user_id <= 0
    ):
        raise LinkChallengeError("Invalid Telegram chat identity.")
    challenge = TelegramLinkChallenge.objects.select_for_update().filter(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        used_at__isnull=True,
    ).first()
    if (
        challenge is None
        or challenge.expires_at < timezone.now()
        or not can_invite_members
    ):
        raise LinkChallengeError("Invalid or insufficient Telegram group authorization.")
    club = Club.objects.select_for_update().get(pk=challenge.club_id)
    owner = User.objects.select_for_update().filter(pk=challenge.expected_owner_id).first()
    if (
        owner is None
        or owner.telegram_user_id != owner_telegram_user_id
        or club.owner_id != owner.pk
        or club.status != ClubStatus.ACTIVE
    ):
        raise LinkChallengeError("Club is not active.")

    try:
        owner_lyceum = get_verified_lyceum(owner)
    except PermissionDenied as exc:
        raise LinkChallengeError("Invalid or insufficient Telegram group authorization.") from exc
    if owner_lyceum.pk != club.lyceum_id:
        raise LinkChallengeError("Invalid or insufficient Telegram group authorization.")

    existing_group = ClubTelegramGroup.objects.select_for_update().filter(club=club).first()
    if existing_group is not None and existing_group.status == TelegramGroupStatus.LINKED:
        raise LinkChallengeError("Telegram group is already linked.")
    try:
        with transaction.atomic():
            defaults = {
                "telegram_chat_id": telegram_chat_id,
                "telegram_chat_title": str(title)[:255],
                "status": TelegramGroupStatus.LINKED,
                "bot_can_invite_members": True,
                "bot_can_send_messages": bool(can_send_messages),
                "linked_at": timezone.now(),
                "unlinked_at": None,
            }
            if existing_group is None:
                group = ClubTelegramGroup.objects.create(club=club, **defaults)
            else:
                for field_name, value in defaults.items():
                    setattr(existing_group, field_name, value)
                existing_group.save(update_fields=(*defaults, "updated_at"))
                group = existing_group
    except IntegrityError as exc:
        raise LinkChallengeError("Telegram group is already linked.") from exc
    challenge.used_at = timezone.now()
    challenge.save(update_fields=("used_at", "updated_at"))
    return group


@transaction.atomic
def unlink_group(*, club_id, user) -> None:  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    club = Club.objects.select_for_update().filter(
        pk=club_id,
        owner=user,
        lyceum=lyceum,
    ).first()
    if club is None:
        raise NotFound("Club not found.")
    group = ClubTelegramGroup.objects.select_for_update().filter(club=club).first()
    if group is not None:
        group.status = TelegramGroupStatus.UNLINKED
        group.unlinked_at = timezone.now()
        group.save(update_fields=("status", "unlinked_at", "updated_at"))


def group_status(*, club_id, user) -> ClubTelegramGroup | None:  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    club = Club.objects.filter(pk=club_id, owner=user, lyceum=lyceum).first()
    if club is None:
        raise NotFound("Club not found.")
    return ClubTelegramGroup.objects.filter(club=club).first()


def create_member_invite(*, club_id, user, client):  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    club = Club.objects.filter(
        pk=club_id,
        lyceum=lyceum,
        status=ClubStatus.ACTIVE,
    ).first()
    if club is None or not ClubMembership.objects.filter(
        club=club,
        user=user,
        status=MembershipStatus.ACTIVE,
    ).exists():
        raise NotFound("Club not found.")
    group = ClubTelegramGroup.objects.filter(
        club=club,
        status=TelegramGroupStatus.LINKED,
        bot_can_invite_members=True,
    ).first()
    if group is None:
        raise LinkChallengeError("Telegram group is not linked.")
    result = client.create_invite_link(
        group.telegram_chat_id,
        expire_date=int((timezone.now() + timedelta(minutes=10)).timestamp()),
        creates_join_request=True,
    )
    invite_link = result.get("invite_link") if isinstance(result, dict) else None
    if not isinstance(invite_link, str) or not invite_link.startswith("https://"):
        raise LinkChallengeError("Telegram did not return a valid invite link.")
    return invite_link
