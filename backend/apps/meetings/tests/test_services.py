from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipRole, MembershipStatus
from apps.notifications.models import Notification, NotificationType
from apps.meetings.models import Meeting, MeetingStatus
from apps.meetings.services import create_meeting, create_announcement

class MeetingServiceTests(TestCase):
    def setUp(self):
        self.lyceum=Lyceum.objects.create(name="Meet Lyceum",code="meet")
        self.user=User.objects.create_user(telegram_user_id=990001)
        StudentRecord.objects.create(lyceum=self.lyceum,first_name="A",last_name="B",group_name="10-A",verified_user=self.user,verified_at=timezone.now())
        self.club=Club.objects.create(lyceum=self.lyceum,owner=self.user,name="Club",short_description="s",description="d",category="OTHER",status=ClubStatus.ACTIVE)
        ClubMembership.objects.create(club=self.club,user=self.user,role=MembershipRole.OWNER,status=MembershipStatus.ACTIVE)
    def test_owner_meeting_notifies_member(self):
        meeting=create_meeting(club_id=self.club.pk,user=self.user,data={"title":"Weekly","description":"","starts_at":timezone.now()+timedelta(days=1),"location":"Room"})
        self.assertEqual(meeting.club_id,self.club.pk)
        self.assertTrue(Notification.objects.filter(recipient=self.user,type=NotificationType.MEETING_CREATED).exists())
    def test_owner_announcement_notifies_member(self):
        create_announcement(club_id=self.club.pk,user=self.user,data={"title":"News","message":"Hello"})
        self.assertTrue(Notification.objects.filter(recipient=self.user,type=NotificationType.ANNOUNCEMENT).exists())
    def test_past_meeting_is_rejected(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            create_meeting(club_id=self.club.pk,user=self.user,data={"title":"Past","description":"","starts_at":timezone.now()-timedelta(minutes=1),"location":""})
