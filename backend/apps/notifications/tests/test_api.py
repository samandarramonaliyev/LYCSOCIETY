from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.identity.models import User
from apps.notifications.models import Notification, NotificationType

class NotificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.one = User.objects.create_user(telegram_user_id=901001)
        self.two = User.objects.create_user(telegram_user_id=901002)

    def test_notifications_are_recipient_scoped_and_read_is_owner_only(self):
        mine = Notification.objects.create(recipient=self.one, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok")
        other = Notification.objects.create(recipient=self.two, type=NotificationType.CLUB_REJECTED, title="Rejected", body="no")
        self.client.force_login(self.one)
        self.assertEqual(len(self.client.get("/api/v1/notifications/", secure=True).json()), 1)
        self.assertEqual(self.client.post(f"/api/v1/notifications/{other.pk}/read/", secure=True).status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/notifications/{mine.pk}/read/", secure=True).status_code, 200)
        mine.refresh_from_db(); self.assertTrue(mine.is_read)
