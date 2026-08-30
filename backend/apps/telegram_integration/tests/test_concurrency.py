from __future__ import annotations

from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.clubs.models import Club, ClubStatus
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.telegram_integration.exceptions import LinkChallengeError
from apps.telegram_integration.models import ClubTelegramGroup
from apps.telegram_integration.services import confirm_link, start_link


class TelegramGroupConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_one_chat_cannot_be_linked_to_two_clubs_concurrently(self) -> None:
        lyceum = Lyceum.objects.create(name="Telegram Race Lyceum", code="tg-race")
        owners: list[User] = []
        clubs: list[Club] = []
        for index in range(2):
            owner = User.objects.create_user(telegram_user_id=882_000_000 + index)
            StudentRecord.objects.create(
                lyceum=lyceum,
                first_name=f"Owner {index}",
                last_name="Student",
                group_name="10-A",
                verified_user=owner,
                verified_at=timezone.now(),
            )
            owners.append(owner)
            clubs.append(
                Club.objects.create(
                    lyceum=lyceum,
                    owner=owner,
                    name=f"Telegram Club {index}",
                    short_description="Short",
                    description="Description",
                    category="OTHER",
                    status=ClubStatus.ACTIVE,
                )
            )
        tokens = [start_link(club_id=club.pk, user=owner) for club, owner in zip(clubs, owners)]
        barrier = Barrier(2)
        outcomes: list[str] = []

        def link(index: int) -> None:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                confirm_link(
                    token=tokens[index],
                    telegram_chat_id=-1_009_999,
                    can_invite_members=True,
                    owner_telegram_user_id=owners[index].telegram_user_id,
                )
                outcomes.append("success")
            except LinkChallengeError:
                outcomes.append("rejected")
            finally:
                connections.close_all()

        threads = [Thread(target=link, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("rejected"), 1)
        self.assertEqual(
            ClubTelegramGroup.objects.filter(telegram_chat_id=-1_009_999).count(),
            1,
        )
