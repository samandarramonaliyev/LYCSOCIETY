from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clubs.models import (
    Club,
    ClubMembership,
    ClubStatus,
    MembershipRole,
    MembershipStatus,
)
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.meetings.models import Announcement, Meeting, MeetingRSVP, MeetingStatus


class MeetingAndAnnouncementApiSecurityTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Meeting API Lyceum", code="meeting-api")
        self.other_lyceum = Lyceum.objects.create(name="Other Lyceum", code="meeting-other")
        self.owner = self.make_user(991_001, self.lyceum, "Owner")
        self.member = self.make_user(991_002, self.lyceum, "Member")
        self.outsider = self.make_user(991_003, self.lyceum, "Outsider")
        self.foreign = self.make_user(991_004, self.other_lyceum, "Foreign")
        self.club = self.make_club(self.owner, self.lyceum, "Meeting Club")
        ClubMembership.objects.create(
            club=self.club,
            user=self.member,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        self.meeting = Meeting.objects.create(
            club=self.club,
            created_by=self.owner,
            title="Upcoming",
            starts_at=timezone.now() + timedelta(days=1),
        )

    def make_user(self, telegram_id: int, lyceum: Lyceum, first_name: str) -> User:
        user = User.objects.create_user(telegram_user_id=telegram_id)
        StudentRecord.objects.create(
            lyceum=lyceum,
            first_name=first_name,
            last_name="Student",
            group_name="10-A",
            verified_user=user,
            verified_at=timezone.now(),
        )
        return user

    def make_club(self, owner: User, lyceum: Lyceum, name: str) -> Club:
        club = Club.objects.create(
            lyceum=lyceum,
            owner=owner,
            name=name,
            short_description="Short",
            description="Description",
            category="OTHER",
            status=ClubStatus.ACTIVE,
        )
        ClubMembership.objects.create(
            club=club,
            user=owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        return club

    def meeting_payload(self, **overrides):  # type: ignore[no-untyped-def]
        payload = {
            "title": "New meeting",
            "description": "Agenda",
            "starts_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "location": "Room 1",
        }
        payload.update(overrides)
        return payload

    def test_only_owner_can_create_and_server_fields_are_rejected(self) -> None:
        url = f"/api/v1/clubs/{self.club.pk}/meetings/"
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(url, self.meeting_payload(), format="json", secure=True).status_code,
            403,
        )

        self.client.force_login(self.owner)
        for field, value in (
            ("status", MeetingStatus.CANCELLED),
            ("created_by", str(self.member.pk)),
            ("club", str(self.club.pk)),
        ):
            response = self.client.post(
                url,
                self.meeting_payload(**{field: value}),
                format="json",
                secure=True,
            )
            self.assertEqual(response.status_code, 400, field)
        self.assertEqual(Meeting.objects.count(), 1)

    def test_meeting_and_announcement_visibility_is_member_and_lyceum_scoped(self) -> None:
        meetings_url = f"/api/v1/clubs/{self.club.pk}/meetings/"
        announcements_url = f"/api/v1/clubs/{self.club.pk}/announcements/"
        for user in (self.outsider, self.foreign):
            self.client.force_login(user)
            self.assertEqual(self.client.get(meetings_url, secure=True).status_code, 404)
            self.assertEqual(self.client.get(announcements_url, secure=True).status_code, 404)

        self.client.force_login(self.member)
        self.assertEqual(self.client.get(meetings_url, secure=True).status_code, 200)
        self.assertEqual(self.client.get(announcements_url, secure=True).status_code, 200)

    def test_meeting_detail_idor_and_cancellation_authorization(self) -> None:
        url = f"/api/v1/meetings/{self.meeting.pk}/"
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url, secure=True).status_code, 404)

        self.client.force_login(self.member)
        self.assertEqual(self.client.patch(url, {}, format="json", secure=True).status_code, 403)

        self.client.force_login(self.owner)
        response = self.client.patch(url, {}, format="json", secure=True)
        self.assertEqual(response.status_code, 200)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, MeetingStatus.CANCELLED)

    def test_rsvp_is_member_only_unique_and_closed_after_cancellation(self) -> None:
        url = f"/api/v1/meetings/{self.meeting.pk}/rsvp/"
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(url, {"response": "GOING"}, format="json", secure=True).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                url,
                {"response": "NOT_GOING"},
                format="json",
                secure=True,
            ).status_code,
            200,
        )
        self.assertEqual(MeetingRSVP.objects.filter(meeting=self.meeting, user=self.member).count(), 1)

        self.meeting.status = MeetingStatus.CANCELLED
        self.meeting.save(update_fields=("status", "updated_at"))
        self.assertEqual(
            self.client.post(url, {"response": "GOING"}, format="json", secure=True).status_code,
            400,
        )

    def test_announcement_authority_fields_are_rejected(self) -> None:
        self.client.force_login(self.owner)
        url = f"/api/v1/clubs/{self.club.pk}/announcements/"
        for field, value in (
            ("created_by", str(self.member.pk)),
            ("club", str(self.club.pk)),
        ):
            response = self.client.post(
                url,
                {"title": "News", "message": "Message", field: value},
                format="json",
                secure=True,
            )
            self.assertEqual(response.status_code, 400, field)
        self.assertFalse(Announcement.objects.exists())
