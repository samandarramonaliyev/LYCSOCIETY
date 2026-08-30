from __future__ import annotations

from django.db import IntegrityError, transaction
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
from apps.meetings.models import Announcement
from apps.reports.models import Report, ReportReason


class ReportApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Report Lyceum", code="report")
        self.other_lyceum = Lyceum.objects.create(name="Other", code="other-report")
        self.user = self.make_user(777_001, self.lyceum, "Reporter")
        self.owner = self.make_user(777_002, self.lyceum, "Owner")
        self.other_user = self.make_user(777_003, self.other_lyceum, "Other")
        self.club = self.make_club(self.owner, self.lyceum, "Visible Club")
        ClubMembership.objects.create(
            club=self.club,
            user=self.user,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        self.announcement = Announcement.objects.create(
            club=self.club,
            created_by=self.owner,
            title="Visible announcement",
            message="Message",
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

    def make_club(self, owner: User, lyceum: Lyceum, name: str, **overrides) -> Club:
        values = {
            "lyceum": lyceum,
            "owner": owner,
            "name": name,
            "short_description": "Short",
            "description": "Description",
            "category": "OTHER",
            "status": ClubStatus.ACTIVE,
        }
        values.update(overrides)
        club = Club.objects.create(**values)
        ClubMembership.objects.create(
            club=club,
            user=owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        return club

    def report(self, **overrides):  # type: ignore[no-untyped-def]
        payload = {
            "target_type": "CLUB",
            "target_id": str(self.club.pk),
            "reason": ReportReason.SPAM,
        }
        payload.update(overrides)
        return self.client.post("/api/v1/reports/", payload, format="json", secure=True)

    def test_verified_student_can_report_visible_targets(self) -> None:
        self.client.force_login(self.user)
        club_response = self.report()
        announcement_response = self.report(
            target_type="ANNOUNCEMENT",
            target_id=str(self.announcement.pk),
            reason=ReportReason.HARASSMENT,
        )

        self.assertEqual(club_response.status_code, 201)
        self.assertEqual(announcement_response.status_code, 201)
        self.assertTrue(Report.objects.filter(reporter=self.user, club=self.club).exists())
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user,
                announcement=self.announcement,
            ).exists()
        )

    def test_reporter_and_moderation_fields_are_rejected(self) -> None:
        self.client.force_login(self.user)
        for field, value in (
            ("reporter", str(self.other_user.pk)),
            ("reviewed_by", str(self.other_user.pk)),
            ("status", "ACTIONED"),
        ):
            response = self.report(**{field: value})
            self.assertEqual(response.status_code, 400, field)
        self.assertFalse(Report.objects.exists())

    def test_unverified_and_cross_lyceum_targets_are_hidden(self) -> None:
        unverified = User.objects.create_user(telegram_user_id=777_004)
        self.client.force_login(unverified)
        self.assertEqual(self.report().status_code, 403)

        self.client.force_login(self.other_user)
        self.assertEqual(self.report().status_code, 404)

    def test_hidden_club_and_nonmember_announcement_are_not_reportable(self) -> None:
        hidden_owner = self.make_user(777_005, self.lyceum, "Hidden Owner")
        hidden_club = self.make_club(
            hidden_owner,
            self.lyceum,
            "Hidden Club",
            status=ClubStatus.PENDING,
        )
        outsider = self.make_user(777_006, self.lyceum, "Outsider")
        self.client.force_login(outsider)

        self.assertEqual(
            self.report(target_id=str(hidden_club.pk)).status_code,
            404,
        )
        self.assertEqual(
            self.report(
                target_type="ANNOUNCEMENT",
                target_id=str(self.announcement.pk),
            ).status_code,
            404,
        )

    def test_invalid_reason_target_and_other_without_details_are_rejected(self) -> None:
        self.client.force_login(self.user)
        self.assertEqual(self.report(reason="NOPE").status_code, 400)
        self.assertEqual(self.report(reason="OTHER").status_code, 400)
        self.assertEqual(self.report(target_type="USER").status_code, 400)

    def test_duplicate_open_report_returns_conflict(self) -> None:
        self.client.force_login(self.user)
        self.assertEqual(self.report().status_code, 201)
        self.assertEqual(self.report().status_code, 409)
        self.assertEqual(Report.objects.count(), 1)

    def test_database_requires_exactly_one_typed_target(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Report.objects.create(
                    reporter=self.user,
                    reason=ReportReason.SPAM,
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Report.objects.create(
                    reporter=self.user,
                    club=self.club,
                    announcement=self.announcement,
                    reason=ReportReason.SPAM,
                )
