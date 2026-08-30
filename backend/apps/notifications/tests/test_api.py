from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.notifications.models import Notification, NotificationType

class NotificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Notify Lyceum", code="notify-api")
        self.one = User.objects.create_user(telegram_user_id=901001)
        self.two = User.objects.create_user(telegram_user_id=901002)
        for index, user in enumerate((self.one, self.two)):
            StudentRecord.objects.create(
                lyceum=self.lyceum,
                first_name=f"Student {index}",
                last_name="Notify",
                group_name="10-A",
                verified_user=user,
                verified_at=timezone.now(),
            )

    def test_notifications_are_recipient_scoped_and_read_is_owner_only(self):
        mine = Notification.objects.create(recipient=self.one, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok")
        other = Notification.objects.create(recipient=self.two, type=NotificationType.CLUB_REJECTED, title="Rejected", body="no")
        self.client.force_login(self.one)
        self.assertEqual(len(self.client.get("/api/v1/notifications/", secure=True).json()), 1)
        self.assertEqual(self.client.post(f"/api/v1/notifications/{other.pk}/read/", secure=True).status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/notifications/{mine.pk}/read/", secure=True).status_code, 200)
        mine.refresh_from_db(); self.assertTrue(mine.is_read)

    def test_preference_mass_assignment_is_rejected(self):
        self.client.force_login(self.one)
        response = self.client.patch(
            "/api/v1/notification-preferences/",
            {"meeting_reminders": False, "user": str(self.two.pk)},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
