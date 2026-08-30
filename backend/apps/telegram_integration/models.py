from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.clubs.models import Club

class TelegramGroupStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    LINKED = "LINKED", "Linked"
    UNLINKED = "UNLINKED", "Unlinked"

class ClubTelegramGroup(UUIDTimeStampedModel):
    club = models.OneToOneField(Club, on_delete=models.CASCADE, related_name="telegram_group")
    telegram_chat_id = models.BigIntegerField(unique=True)
    telegram_chat_title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=TelegramGroupStatus.choices, default=TelegramGroupStatus.LINKED)
    bot_can_invite_members = models.BooleanField(default=False)
    bot_can_send_messages = models.BooleanField(default=False)
    linked_at = models.DateTimeField(null=True, blank=True)
    unlinked_at = models.DateTimeField(null=True, blank=True)

class TelegramLinkChallenge(UUIDTimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="telegram_link_challenges")
    expected_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="telegram_link_challenges",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class TelegramWebhookUpdate(UUIDTimeStampedModel):
    """Minimal durable idempotency record; raw update contents are never stored."""

    update_id = models.PositiveBigIntegerField(unique=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
