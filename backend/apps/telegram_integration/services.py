import hashlib, secrets
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.lyceums.services.scoping import get_verified_lyceum
from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from .models import ClubTelegramGroup, TelegramGroupStatus, TelegramLinkChallenge
from .exceptions import LinkChallengeError

def start_link(*, club_id, user):
    club = Club.objects.filter(pk=club_id, owner=user, lyceum=get_verified_lyceum(user), status=ClubStatus.ACTIVE).first()
    if not club: raise PermissionDenied("Only an active club owner may link a group.")
    token = secrets.token_urlsafe(32)
    TelegramLinkChallenge.objects.filter(club=club, used_at__isnull=True).update(used_at=timezone.now())
    TelegramLinkChallenge.objects.create(club=club, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=timezone.now()+timedelta(minutes=10))
    return token

@transaction.atomic
def confirm_link(*, token, telegram_chat_id, title="", can_invite_members=False, can_send_messages=False):
    challenge = TelegramLinkChallenge.objects.select_for_update().filter(token_hash=hashlib.sha256(token.encode()).hexdigest(), used_at__isnull=True).first()
    if not challenge or challenge.expires_at < timezone.now() or not can_invite_members: raise LinkChallengeError("Invalid or insufficient Telegram group authorization.")
    club = Club.objects.select_for_update().get(pk=challenge.club_id)
    if club.status != ClubStatus.ACTIVE: raise LinkChallengeError("Club is not active.")
    existing = ClubTelegramGroup.objects.filter(telegram_chat_id=telegram_chat_id).exclude(club=club).exists()
    if existing: raise LinkChallengeError("Telegram group is already linked.")
    group, _ = ClubTelegramGroup.objects.update_or_create(club=club, defaults={"telegram_chat_id":telegram_chat_id,"telegram_chat_title":title[:255],"status":TelegramGroupStatus.LINKED,"bot_can_invite_members":True,"bot_can_send_messages":can_send_messages,"linked_at":timezone.now(),"unlinked_at":None})
    challenge.used_at = timezone.now(); challenge.save(update_fields=("used_at", "updated_at"))
    return group

def unlink_group(*, club_id, user):
    club = Club.objects.filter(pk=club_id, owner=user, lyceum=get_verified_lyceum(user)).first()
    if not club: raise PermissionDenied
    group = ClubTelegramGroup.objects.filter(club=club).first()
    if group: group.status=TelegramGroupStatus.UNLINKED; group.unlinked_at=timezone.now(); group.save(update_fields=("status","unlinked_at","updated_at"))

def create_member_invite(*, club_id, user, client):
    lyceum = get_verified_lyceum(user)
    club = Club.objects.filter(pk=club_id, lyceum=lyceum, status=ClubStatus.ACTIVE).first()
    if not club or not ClubMembership.objects.filter(club=club,user=user,status=MembershipStatus.ACTIVE).exists(): raise PermissionDenied
    group = ClubTelegramGroup.objects.filter(club=club,status=TelegramGroupStatus.LINKED,bot_can_invite_members=True).first()
    if not group: raise LinkChallengeError("Telegram group is not linked.")
    return client.create_invite_link(group.telegram_chat_id, member_limit=1, expire_date=int((timezone.now()+timedelta(minutes=10)).timestamp())).get("invite_link")
