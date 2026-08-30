from __future__ import annotations

from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.clubs.models import (
    Club,
    ClubMembership,
    ClubStatus,
    JoinRequest,
    MembershipRole,
    MembershipStatus,
)
from apps.clubs.services import (
    ClubAlreadyOwned,
    JoinRequestConflict,
    MembershipLimitReached,
    accept_join_request,
    create_club,
    create_join_request,
)
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord


class ClubConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.lyceum = Lyceum.objects.create(name="Concurrency Lyceum", code="club-races")
        self.next_telegram_id = 881_000_000

    def make_user(self, first_name: str) -> User:
        self.next_telegram_id += 1
        user = User.objects.create_user(telegram_user_id=self.next_telegram_id)
        StudentRecord.objects.create(
            lyceum=self.lyceum,
            first_name=first_name,
            last_name="Student",
            group_name="10-A",
            verified_user=user,
            verified_at=timezone.now(),
        )
        return user

    def make_club(self, owner: User, name: str) -> Club:
        club = Club.objects.create(
            lyceum=self.lyceum,
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

    def run_two(self, worker) -> list[str]:  # type: ignore[no-untyped-def]
        barrier = Barrier(2)
        outcomes: list[str] = []

        def wrapped(index: int) -> None:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                outcomes.append(worker(index))
            finally:
                close_old_connections()

        threads = [Thread(target=wrapped, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return outcomes

    def test_one_club_per_owner_survives_concurrent_creation(self) -> None:
        user = self.make_user("Founder")

        def worker(index: int) -> str:
            try:
                create_club(
                    user=User.objects.get(pk=user.pk),
                    validated_data={
                        "name": f"Club {index}",
                        "short_description": "Short",
                        "description": "Description",
                        "category": "OTHER",
                    },
                )
                return "success"
            except ClubAlreadyOwned:
                return "rejected"

        outcomes = self.run_two(worker)

        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("rejected"), 1)
        self.assertEqual(Club.objects.filter(owner=user).count(), 1)
        self.assertEqual(
            ClubMembership.objects.filter(
                user=user,
                role=MembershipRole.OWNER,
                status=MembershipStatus.ACTIVE,
            ).count(),
            1,
        )

    def test_membership_limit_survives_two_simultaneous_acceptances(self) -> None:
        student = self.make_user("Applicant")
        existing_owners = [self.make_user("Existing One"), self.make_user("Existing Two")]
        for index, owner in enumerate(existing_owners):
            club = self.make_club(owner, f"Existing {index}")
            ClubMembership.objects.create(
                club=club,
                user=student,
                role=MembershipRole.MEMBER,
                status=MembershipStatus.ACTIVE,
            )
        candidate_owners = [self.make_user("Owner One"), self.make_user("Owner Two")]
        candidates = [
            self.make_club(owner, f"Candidate {index}")
            for index, owner in enumerate(candidate_owners)
        ]
        requests = [JoinRequest.objects.create(club=club, user=student) for club in candidates]

        def worker(index: int) -> str:
            try:
                accept_join_request(
                    request_id=requests[index].pk,
                    owner=User.objects.get(pk=candidate_owners[index].pk),
                )
                return "success"
            except MembershipLimitReached:
                return "limited"

        outcomes = self.run_two(worker)

        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("limited"), 1)
        self.assertEqual(
            ClubMembership.objects.filter(
                user=student,
                status=MembershipStatus.ACTIVE,
            ).count(),
            3,
        )

    def test_duplicate_pending_request_survives_concurrent_submission(self) -> None:
        owner = self.make_user("Owner")
        student = self.make_user("Applicant")
        club = self.make_club(owner, "Target")

        def worker(index: int) -> str:
            try:
                create_join_request(club_id=club.pk, user=User.objects.get(pk=student.pk))
                return "success"
            except JoinRequestConflict:
                return "duplicate"

        outcomes = self.run_two(worker)

        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("duplicate"), 1)
        self.assertEqual(JoinRequest.objects.filter(club=club, user=student).count(), 1)
