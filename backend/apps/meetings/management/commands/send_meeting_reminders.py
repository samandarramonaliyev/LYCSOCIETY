from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.clubs.models import ClubMembership, MembershipStatus
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification
from apps.notifications.models import NotificationPreference
from apps.meetings.models import Meeting, MeetingStatus
class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        now=timezone.now(); end=now+timedelta(hours=1)
        for meeting in Meeting.objects.filter(status=MeetingStatus.SCHEDULED,starts_at__gt=now,starts_at__lte=end):
            for m in ClubMembership.objects.filter(club=meeting.club,status=MembershipStatus.ACTIVE):
                p=NotificationPreference.objects.filter(user=m.user).first()
                if p and not p.meeting_reminders: continue
                create_notification(recipient=m.user,type=NotificationType.MEETING_REMINDER,title="Meeting reminder",body=meeting.title,dedupe_key=f"meeting:{meeting.pk}:reminder:{m.user_id}")
