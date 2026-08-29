from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.identity.models import AccountStatus, User
from apps.lyceums.models import Lyceum, StudentRecord, StudentRecordStatus
from apps.lyceums.services.scoping import (
    VerifiedLyceumUnavailable,
    get_verified_lyceum,
    scope_queryset_to_verified_lyceum,
)

from apps.profiles.models import Interest


class ProfileApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")
        self.other_lyceum = Lyceum.objects.create(name="Samarkand Lyceum", code="samarkand-1")
        self.user = User.objects.create_user(
            telegram_user_id=630_000_001,
            telegram_first_name="Telegram",
        )
        self.record = StudentRecord.objects.create(
            lyceum=self.lyceum,
            external_student_key="profile-student",
            first_name="  Sam ",
            last_name="Karimov",
            group_name="10-B",
            verified_user=self.user,
            verified_at=timezone.now(),
        )
        self.interests = [
            Interest.objects.create(name="Programming", slug="programming"),
            Interest.objects.create(name="Chess", slug="chess"),
            Interest.objects.create(name="Inactive", slug="inactive", is_active=False),
        ]

    def authenticate(self, user: User | None = None) -> None:
        self.client.force_login(user or self.user)

    def test_verified_user_retrieves_safe_self_profile(self) -> None:
        self.authenticate()
        self.user.profile.about = "Hello"
        self.user.profile.interests.add(self.interests[0])
        self.user.profile.save(update_fields=("about", "updated_at"))

        response = self.client.get("/api/v1/profile/", secure=True)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["first_name"], "  Sam ")
        self.assertEqual(data["last_name"], "Karimov")
        self.assertEqual(data["group"], "10-B")
        self.assertEqual(data["lyceum"]["id"], str(self.lyceum.id))
        self.assertEqual(data["about"], "Hello")
        self.assertEqual(data["interests"][0]["name"], "Programming")
        for secret in ("external_student_key", str(self.record.id), "verified_at"):
            self.assertNotIn(secret, response.content.decode())

    def test_unverified_and_suspended_users_cannot_retrieve_or_update_profile(self) -> None:
        unverified = User.objects.create_user(telegram_user_id=630_000_002)
        self.authenticate(unverified)
        self.assertEqual(self.client.get("/api/v1/profile/", secure=True).status_code, 403)
        self.assertEqual(
            self.client.patch("/api/v1/profile/", {"about": "x"}, format="json", secure=True).status_code,
            403,
        )

        self.user.status = AccountStatus.SUSPENDED
        self.user.save(update_fields=("status", "updated_at"))
        self.authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/profile/", secure=True).status_code, 403)

    def test_editable_fields_are_trimmed_and_photo_requires_https(self) -> None:
        self.authenticate()
        response = self.client.patch(
            "/api/v1/profile/",
            {
                "about": "  about text  ",
                "hobbies": " chess   reading ",
                "profile_photo_url": " https://cdn.example.test/photo.jpg ",
            },
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.about, "about text")
        self.assertEqual(self.user.profile.hobbies, "chess reading")
        self.assertEqual(self.user.profile.profile_photo_url, "https://cdn.example.test/photo.jpg")

        invalid = self.client.patch(
            "/api/v1/profile/",
            {"profile_photo_url": "http://example.test/photo.jpg"},
            format="json",
            secure=True,
        )
        self.assertEqual(invalid.status_code, 400)

    def test_verified_fields_and_unknown_fields_are_rejected(self) -> None:
        self.authenticate()
        original = (self.record.first_name, self.record.group_name, self.record.lyceum_id)
        for field, value in (
            ("first_name", "Fake"),
            ("last_name", "Fake"),
            ("group", "11-A"),
            ("lyceum", str(self.other_lyceum.id)),
            ("lyceum_id", str(self.other_lyceum.id)),
            ("official_student_record", str(self.record.id)),
            ("user_id", "other"),
        ):
            response = self.client.patch(
                "/api/v1/profile/", {field: value}, format="json", secure=True
            )
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json()["error"]["fields"])
        self.record.refresh_from_db()
        self.assertEqual((self.record.first_name, self.record.group_name, self.record.lyceum_id), original)

    def test_interest_list_excludes_inactive_and_supports_search(self) -> None:
        self.authenticate()
        response = self.client.get("/api/v1/interests/?search=prog", secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["results"]], ["Programming"])
        all_interests = self.client.get("/api/v1/interests/", secure=True)
        self.assertNotIn("Inactive", all_interests.content.decode())

    def test_interest_selection_is_atomic_deduplicated_and_replaced(self) -> None:
        self.authenticate()
        first, second = self.interests[:2]
        response = self.client.patch(
            "/api/v1/profile/",
            {"interest_ids": [str(first.id), str(first.id), str(second.id)]},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.profile.interests.count(), 2)

        response = self.client.patch(
            "/api/v1/profile/",
            {"interest_ids": [str(second.id)]},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.user.profile.interests.values_list("id", flat=True)), [second.id])

    def test_missing_inactive_and_too_many_interests_fail_without_overwriting(self) -> None:
        self.authenticate()
        first = self.interests[0]
        self.user.profile.interests.add(first)
        inactive = self.interests[2]
        response = self.client.patch(
            "/api/v1/profile/",
            {"interest_ids": [str(inactive.id)]},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.user.profile.interests.values_list("id", flat=True)), [first.id])

        extra = [Interest.objects.create(name=f"Tag {i}", slug=f"tag-{i}") for i in range(11)]
        response = self.client.patch(
            "/api/v1/profile/",
            {"interest_ids": [str(item.id) for item in extra]},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.user.profile.interests.values_list("id", flat=True)), [first.id])


class LyceumScopeTests(TestCase):
    def setUp(self) -> None:
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")
        self.other = Lyceum.objects.create(name="Samarkand Lyceum", code="samarkand-1")
        self.user = User.objects.create_user(telegram_user_id=630_000_010)
        StudentRecord.objects.create(
            lyceum=self.lyceum,
            first_name="Sam",
            last_name="Karimov",
            group_name="10-B",
            verified_user=self.user,
            verified_at=timezone.now(),
        )

    def test_scope_is_derived_from_verified_record_not_client_input(self) -> None:
        self.assertEqual(get_verified_lyceum(self.user), self.lyceum)
        scoped = scope_queryset_to_verified_lyceum(Lyceum.objects.all(), user=self.user)
        self.assertEqual(list(scoped), [self.lyceum])

    def test_inactive_verified_record_has_no_trusted_scope(self) -> None:
        record = self.user.student_record
        record.status = StudentRecordStatus.INACTIVE
        record.save(update_fields=("status", "updated_at"))
        with self.assertRaises(VerifiedLyceumUnavailable):
            get_verified_lyceum(self.user)
