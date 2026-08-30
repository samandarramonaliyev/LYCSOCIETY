from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.profiles.models import Interest

from apps.clubs.models import (
    Club,
    ClubMembership,
    ClubStatus,
    JoinRequest,
    JoinRequestStatus,
    MembershipRole,
    MembershipStatus,
)
from apps.clubs.services import moderate_club


class ClubApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")
        self.other_lyceum = Lyceum.objects.create(name="Samarkand Lyceum", code="samarkand-1")
        self.interest = Interest.objects.create(name="Programming", slug="programming")
        self.owner = self.make_user(640_000_001, self.lyceum, "Owner")
        self.student = self.make_user(640_000_002, self.lyceum, "Student")
        self.other_student = self.make_user(640_000_003, self.other_lyceum, "Other")

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

    def club_payload(self, **overrides):
        payload = {
            "name": "Python Club",
            "short_description": "Learn Python",
            "description": "A club for programming.",
            "category": "TECHNOLOGY",
            "interest_ids": [str(self.interest.id)],
        }
        payload.update(overrides)
        return payload

    def create_pending(self, owner: User | None = None) -> Club:
        self.client.force_login(owner or self.owner)
        response = self.client.post("/api/v1/clubs/", self.club_payload(), format="json", secure=True)
        self.assertEqual(response.status_code, 201)
        return Club.objects.get(owner=owner or self.owner)

    def activate(self, club: Club) -> None:
        moderate_club(club_id=club.pk, action="approve")

    def test_verified_student_creates_pending_club_with_trusted_lyceum_and_owner_membership(self) -> None:
        club = self.create_pending()
        self.assertEqual(club.status, ClubStatus.PENDING)
        self.assertEqual(club.lyceum_id, self.lyceum.id)
        membership = ClubMembership.objects.get(club=club, user=self.owner)
        self.assertEqual(membership.role, MembershipRole.OWNER)

    def test_client_cannot_override_owner_or_lyceum_and_second_club_is_rejected(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.post(
            "/api/v1/clubs/",
            self.club_payload(owner=str(self.student.id), lyceum=str(self.other_lyceum.id), status="ACTIVE"),
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Club.objects.count(), 0)
        club = self.create_pending()
        second = self.client.post("/api/v1/clubs/", self.club_payload(name="Second"), format="json", secure=True)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(Club.objects.count(), 1)
        self.assertEqual(club.owner_id, self.owner.id)

    def test_unverified_student_cannot_create_and_admin_moderation_requires_reason(self) -> None:
        unverified = User.objects.create_user(telegram_user_id=640_000_004)
        self.client.force_login(unverified)
        self.assertEqual(self.client.post("/api/v1/clubs/", self.club_payload(), format="json", secure=True).status_code, 403)

        club = self.create_pending()
        admin = User.objects.create_superuser(telegram_user_id=640_000_005, password="test-password")
        self.client.force_login(admin)
        missing_reason = self.client.post(
            f"/api/v1/clubs/{club.id}/moderate/", {"action": "reject"}, format="json", secure=True
        )
        self.assertEqual(missing_reason.status_code, 400)
        rejected = self.client.post(
            f"/api/v1/clubs/{club.id}/moderate/",
            {"action": "reject", "reason": "Please clarify the club purpose."},
            format="json",
            secure=True,
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], ClubStatus.REJECTED)

    def test_discovery_and_detail_are_active_same_lyceum_only(self) -> None:
        own = self.create_pending()
        self.activate(own)
        other = self.create_pending(self.other_student)
        self.activate(other)
        self.client.force_login(self.student)
        listing = self.client.get("/api/v1/clubs/?search=python&category=technology&interest=" + str(self.interest.id), secure=True)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([row["id"] for row in listing.json()["results"]], [str(own.id)])
        own_detail = self.client.get(f"/api/v1/clubs/{own.id}/", secure=True)
        other_detail = self.client.get(f"/api/v1/clubs/{other.id}/", secure=True)
        self.assertEqual(own_detail.status_code, 200)
        self.assertEqual(other_detail.status_code, 404)

    def test_join_accept_reject_cancel_and_owner_leave_rules(self) -> None:
        club = self.create_pending()
        self.activate(club)
        self.client.force_login(self.student)
        request_response = self.client.post(f"/api/v1/clubs/{club.id}/join-requests/", {}, format="json", secure=True)
        self.assertEqual(request_response.status_code, 201)
        request_id = request_response.json()["id"]
        duplicate = self.client.post(f"/api/v1/clubs/{club.id}/join-requests/", {}, format="json", secure=True)
        self.assertEqual(duplicate.status_code, 409)

        self.client.force_login(self.owner)
        accepted = self.client.post(f"/api/v1/join-requests/{request_id}/accept/", {}, format="json", secure=True)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(JoinRequest.objects.get(id=request_id).status, JoinRequestStatus.ACCEPTED)
        self.assertTrue(ClubMembership.objects.filter(club=club, user=self.student, status=MembershipStatus.ACTIVE).exists())
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(f"/api/v1/clubs/{club.id}/leave/", {}, format="json", secure=True).status_code, 204)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(f"/api/v1/clubs/{club.id}/leave/", {}, format="json", secure=True).status_code, 409)

    def test_rejected_club_can_be_resubmitted_without_new_row(self) -> None:
        club = self.create_pending()
        moderate_club(club_id=club.pk, action="reject", reason="Needs more detail")
        self.client.force_login(self.owner)
        response = self.client.post(f"/api/v1/clubs/{club.id}/resubmit/", {}, format="json", secure=True)
        self.assertEqual(response.status_code, 200)
        club.refresh_from_db()
        self.assertEqual(club.status, ClubStatus.PENDING)
        self.assertEqual(club.rejection_reason, "")
        self.assertEqual(Club.objects.filter(owner=self.owner).count(), 1)

    def test_join_request_actions_hide_objects_from_unrelated_students_and_owners(self) -> None:
        club = self.create_pending()
        self.activate(club)
        self.client.force_login(self.student)
        created = self.client.post(
            f"/api/v1/clubs/{club.id}/join-requests/",
            {},
            format="json",
            secure=True,
        )
        request_id = created.json()["id"]

        unrelated = self.make_user(640_000_006, self.lyceum, "Unrelated")
        self.client.force_login(unrelated)
        self.assertEqual(
            self.client.post(
                f"/api/v1/join-requests/{request_id}/cancel/",
                {},
                format="json",
                secure=True,
            ).status_code,
            404,
        )

        other_owner = self.make_user(640_000_007, self.lyceum, "Other Owner")
        other_club = Club.objects.create(
            lyceum=self.lyceum,
            owner=other_owner,
            name="Other Club",
            short_description="Other",
            description="Other",
            category="OTHER",
            status=ClubStatus.ACTIVE,
        )
        ClubMembership.objects.create(
            club=other_club,
            user=other_owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        self.client.force_login(other_owner)
        for action in ("accept", "reject"):
            response = self.client.post(
                f"/api/v1/join-requests/{request_id}/{action}/",
                {},
                format="json",
                secure=True,
            )
            self.assertEqual(response.status_code, 404)
        self.assertEqual(
            JoinRequest.objects.get(pk=request_id).status,
            JoinRequestStatus.PENDING,
        )

    def test_member_cannot_assign_owner_role(self) -> None:
        club = self.create_pending()
        self.activate(club)
        self.client.force_login(self.student)
        response = self.client.post(
            f"/api/v1/clubs/{club.id}/join-requests/",
            {"role": "OWNER"},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(JoinRequest.objects.filter(club=club, user=self.student).exists())
