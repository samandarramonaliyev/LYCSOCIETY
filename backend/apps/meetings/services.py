from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from apps.notifications.models import NotificationType, NotificationPreference
from apps.notifications.services import create_notification
from .models import Meeting, MeetingStatus, Announcement

def _club(club_id, user, owner=False):
    if not user.can_access_student_features: raise PermissionDenied("An active verified student is required.")
    club=Club.objects.filter(pk=club_id, status=ClubStatus.ACTIVE, lyceum__student_records__verified_user=user).distinct().first()
    if not club or not ClubMembership.objects.filter(club=club,user=user,status=MembershipStatus.ACTIVE).exists(): raise NotFound("Club not found.")
    if owner and club.owner_id != user.pk: raise PermissionDenied
    return club
def _notify(club, typ, title, body, pref, key):
    for m in ClubMembership.objects.filter(club=club,status=MembershipStatus.ACTIVE).select_related("user"):
        p=NotificationPreference.objects.filter(user=m.user).first()
        if p is not None and not getattr(p,pref): continue
        create_notification(recipient=m.user,type=typ,title=title,body=body,dedupe_key=f"{key}:{m.user_id}")
@transaction.atomic
def create_meeting(*, club_id, user, data):
    club=_club(club_id,user,True)
    if data["starts_at"]<=timezone.now(): raise ValidationError("Meeting must be in the future.")
    obj=Meeting.objects.create(club=club,created_by=user,**data)
    _notify(club,NotificationType.MEETING_CREATED,"New meeting",obj.title,"meeting_notifications",f"meeting:{obj.pk}:created")
    return obj
@transaction.atomic
def create_announcement(*, club_id, user, data):
    club=_club(club_id,user,True); obj=Announcement.objects.create(club=club,created_by=user,**data)
    _notify(club,NotificationType.ANNOUNCEMENT,obj.title,obj.message,"club_announcements",f"announcement:{obj.pk}"); return obj
def accessible_meeting(meeting_id,user):
    if not user.can_access_student_features: raise PermissionDenied("An active verified student is required.")
    obj=Meeting.objects.select_related("club").filter(pk=meeting_id).first()
    if not obj or not ClubMembership.objects.filter(club=obj.club,user=user,status=MembershipStatus.ACTIVE).exists(): raise NotFound("Meeting not found.")
    return obj
@transaction.atomic
def cancel_meeting(*,meeting_id,user):
    obj=accessible_meeting(meeting_id,user)
    if obj.club.owner_id!=user.pk: raise PermissionDenied
    obj.status=MeetingStatus.CANCELLED; obj.save(update_fields=("status","updated_at")); return obj
