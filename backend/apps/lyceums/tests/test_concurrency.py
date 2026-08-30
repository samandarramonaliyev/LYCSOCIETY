from __future__ import annotations

from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase

from apps.identity.exceptions import VerificationClaimFailed
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.lyceums.services.verification import claim_student_record


class RosterClaimConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_two_users_cannot_claim_the_same_record_concurrently(self) -> None:
        lyceum = Lyceum.objects.create(name="Concurrent Lyceum", code="claim-race")
        record = StudentRecord.objects.create(
            lyceum=lyceum,
            first_name="Same",
            last_name="Student",
            group_name="10-A",
        )
        users = [
            User.objects.create_user(telegram_user_id=880_000_001),
            User.objects.create_user(telegram_user_id=880_000_002),
        ]
        barrier = Barrier(2)
        outcomes: list[str] = []

        def claim(user_id) -> None:  # type: ignore[no-untyped-def]
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                barrier.wait(timeout=10)
                claim_student_record(
                    user=user,
                    lyceum_id=lyceum.pk,
                    first_name="Same",
                    last_name="Student",
                    group_name="10-A",
                )
                outcomes.append("success")
            except VerificationClaimFailed:
                outcomes.append("rejected")
            finally:
                connections.close_all()

        threads = [Thread(target=claim, args=(user.pk,)) for user in users]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("rejected"), 1)
        record.refresh_from_db()
        self.assertIn(record.verified_user_id, {user.pk for user in users})
        self.assertEqual(
            StudentRecord.objects.filter(verified_user__in=users).count(),
            1,
        )
