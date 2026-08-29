from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel

class NotificationType(models.TextChoices):
    CLUB_APPROVED = "CLUB_APPROVED", "Club approved"
    CLUB_REJECTED = "CLUB_REJECTED", "Club rejected"
    JOIN_REQUEST_CREATED = "JOIN_REQUEST_CREATED", "Join request created"
    JOIN_REQUEST_ACCEPTED = "JOIN_REQUEST_ACCEPTED", "Join request accepted"
    JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED", "Join request rejected"
    MEETING_CREATED = "MEETING_CREATED", "Meeting created"
    MEETING_REMINDER = "MEETING_REMINDER", "Meeting reminder"
    ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"

class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"

class Notification(UUIDTimeStampedModel):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications")
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False, db_index=True)
    delivery_status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    delivery_attempts = models.PositiveSmallIntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_delivery_error = models.CharField(max_length=500, blank=True)
    dedupe_key = models.CharField(max_length=255, unique=True, null=True, blank=True)

class NotificationPreference(UUIDTimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    club_announcements = models.BooleanField(default=True)
    meeting_notifications = models.BooleanField(default=True)
    meeting_reminders = models.BooleanField(default=True)
