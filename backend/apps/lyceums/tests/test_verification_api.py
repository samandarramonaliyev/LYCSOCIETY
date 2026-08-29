from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework.test import APIClient, APIRequestFactory

from apps.common.permissions import IsVerifiedActiveStudent
from apps.identity.models import AccountStatus, User
from apps.lyceums.models import Lyceum, LyceumStatus, StudentRecord, StudentRecordStatus
from apps.profiles.models import StudentProfile


class StudentVerificationApiTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")
        self.user = User.objects.create_user(telegram_user_id=620_000_001)

    def create_record(self, *, external_student_key: str, **overrides) -> StudentRecord:
        values = {
            "lyceum": self.lyceum,
            "external_student_key": external_student_key,
            "first_name": "Sam",
            "last_name": "Karimov",
            "group_name": "10-B",
        }
        values.update(overrides)
        return StudentRecord.objects.create(**values)

    def claim(self, user: User, **overrides):
        self.client.force_login(user)
        payload = {
            "lyceum_id": str(self.lyceum.id),
            "first_name": "  sam ",
            "last_name": "KARIMOV",
            "group": "  10-b ",
        }
        payload.update(overrides)
        return self.client.post(
            "/api/v1/verification/claim/",
            payload,
            format="json",
            secure=True,
        )

    def test_only_an_authenticated_user_may_attempt_verification(self) -> None:
        response = self.client.post(
            "/api/v1/verification/claim/",
            {
                "lyceum_id": str(self.lyceum.id),
                "first_name": "Sam",
                "last_name": "Karimov",
                "group": "10-B",
            },
            format="json",
            secure=True,
        )

        self.assertEqual(response.status_code, 403)

    def test_unique_normalized_match_claims_the_official_record(self) -> None:
        record = self.create_record(external_student_key="student-001")

        response = self.claim(self.user)

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(record.verified_user, self.user)
        self.assertIsNotNone(record.verified_at)
        self.assertTrue(self.user.can_access_student_features)
        self.assertTrue(StudentProfile.objects.filter(user=self.user).exists())
        verified_student = response.json()["user"]["verified_student"]
        self.assertEqual(verified_student["first_name"], "Sam")
        self.assertEqual(verified_student["last_name"], "Karimov")
        self.assertEqual(verified_student["group"], "10-B")
        self.assertEqual(verified_student["lyceum"]["id"], str(self.lyceum.id))

    def test_zero_match_returns_a_generic_failure_without_claiming_any_record(self) -> None:
        self.create_record(external_student_key="student-002")

        response = self.claim(self.user, group="wrong-group")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VERIFICATION_FAILED")
        self.assertFalse(StudentRecord.objects.get(external_student_key="student-002").is_claimed)

    def test_ambiguous_and_already_claimed_records_return_the_same_generic_failure(self) -> None:
        zero_match_response = self.claim(self.user, group="wrong-group")
        self.create_record(external_student_key="student-003")
        self.create_record(external_student_key="student-004")
        ambiguous_user = User.objects.create_user(telegram_user_id=620_000_002)
        ambiguous_response = self.claim(ambiguous_user)

        claimed_record = self.create_record(
            external_student_key="student-claimed",
            first_name="Grace",
            last_name="Hopper",
            group_name="11-A",
        )
        owner = User.objects.create_user(telegram_user_id=620_000_003)
        claimed_record.verified_user = owner
        claimed_record.verified_at = timezone.now()
        claimed_record.save(update_fields=("verified_user", "verified_at", "updated_at"))
        claimed_user = User.objects.create_user(telegram_user_id=620_000_004)
        claimed_response = self.claim(
            claimed_user,
            first_name="Grace",
            last_name="Hopper",
            group="11-A",
        )

        self.assertEqual(ambiguous_response.status_code, 400)
        self.assertEqual(claimed_response.status_code, 400)
        self.assertEqual(ambiguous_response.json(), zero_match_response.json())
        self.assertEqual(claimed_response.json(), zero_match_response.json())
        claimed_record.refresh_from_db()
        self.assertEqual(claimed_record.verified_user, owner)
        self.assertFalse(ambiguous_user.is_verified)
        self.assertFalse(claimed_user.is_verified)

    def test_already_verified_user_cannot_claim_another_identity(self) -> None:
        self.create_record(external_student_key="student-005")
        second_record = self.create_record(
            external_student_key="student-006",
            first_name="Ada",
            last_name="Lovelace",
            group_name="11-A",
        )

        self.assertEqual(self.claim(self.user).status_code, 200)
        second_response = self.claim(
            self.user,
            first_name="Ada",
            last_name="Lovelace",
            group="11-A",
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json()["error"]["code"], "ALREADY_VERIFIED")
        second_record.refresh_from_db()
        self.assertFalse(second_record.is_claimed)

    def test_client_cannot_claim_a_match_from_another_lyceum(self) -> None:
        self.create_record(external_student_key="student-007")
        other_lyceum = Lyceum.objects.create(name="Samarkand Lyceum", code="samarkand-1")

        response = self.claim(self.user, lyceum_id=str(other_lyceum.id))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VERIFICATION_FAILED")
        self.assertFalse(self.user.is_verified)

    def test_inactive_record_or_lyceum_cannot_be_claimed(self) -> None:
        inactive_record = self.create_record(
            external_student_key="student-008",
            status=StudentRecordStatus.INACTIVE,
        )

        inactive_record_response = self.claim(self.user)

        self.assertEqual(inactive_record_response.status_code, 400)
        inactive_record.status = StudentRecordStatus.ACTIVE
        inactive_record.save(update_fields=("status", "updated_at"))
        self.lyceum.status = LyceumStatus.INACTIVE
        self.lyceum.save(update_fields=("status", "updated_at"))
        inactive_lyceum_response = self.claim(self.user)

        self.assertEqual(inactive_lyceum_response.status_code, 400)
        self.assertFalse(inactive_record.is_claimed)

    def test_me_response_uses_verified_database_fields_and_hides_roster_internals(self) -> None:
        record = self.create_record(external_student_key="sensitive-student-key")
        self.assertEqual(self.claim(self.user).status_code, 200)
        self.user.profile.about = "Chess and programming"
        self.user.profile.save(update_fields=("about", "updated_at"))

        response = self.client.get("/api/v1/auth/me/", secure=True)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verified_student"]["group"], record.group_name)
        self.assertEqual(data["profile"]["about"], "Chess and programming")
        self.assertNotIn("external_student_key", response.content.decode())
        self.assertNotIn(str(record.id), response.content.decode())
        self.assertNotIn(str(self.user.telegram_user_id), response.content.decode())

    def test_verified_fields_are_not_profile_fields_and_cannot_be_changed_through_profile_data(self) -> None:
        self.create_record(external_student_key="student-009")
        self.assertEqual(self.claim(self.user).status_code, 200)
        profile = self.user.profile
        profile.about = "Editable information"
        profile.save(update_fields=("about", "updated_at"))

        profile_field_names = {field.name for field in StudentProfile._meta.fields}
        self.assertNotIn("lyceum", profile_field_names)
        self.assertNotIn("group_name", profile_field_names)
        self.assertNotIn("first_name", profile_field_names)
        self.assertNotIn("last_name", profile_field_names)
        self.assertEqual(profile.verified_lyceum, self.lyceum)
        self.assertEqual(profile.verified_group_name, "10-B")

    def test_verification_status_exposes_only_onboarding_state(self) -> None:
        self.client.force_login(self.user)
        unverified_response = self.client.get("/api/v1/verification/status/", secure=True)
        self.create_record(external_student_key="student-010")
        self.assertEqual(self.claim(self.user).status_code, 200)
        verified_response = self.client.get("/api/v1/verification/status/", secure=True)

        self.assertEqual(unverified_response.json()["verification_status"], "UNVERIFIED")
        self.assertFalse(unverified_response.json()["can_access_student_features"])
        self.assertEqual(verified_response.json()["verification_status"], "VERIFIED")
        self.assertTrue(verified_response.json()["can_access_student_features"])
        self.assertNotIn("external_student_key", verified_response.content.decode())

    def test_authenticated_onboarding_can_list_only_active_lyceum_choices(self) -> None:
        inactive_lyceum = Lyceum.objects.create(
            name="Inactive Lyceum",
            code="inactive-1",
            status=LyceumStatus.INACTIVE,
        )

        anonymous_response = self.client.get("/api/v1/verification/lyceums/", secure=True)
        self.client.force_login(self.user)
        authenticated_response = self.client.get(
            "/api/v1/verification/lyceums/",
            secure=True,
        )

        self.assertEqual(anonymous_response.status_code, 403)
        self.assertEqual(authenticated_response.status_code, 200)
        self.assertEqual(
            authenticated_response.json()["results"],
            [
                {
                    "id": str(self.lyceum.id),
                    "code": self.lyceum.code,
                    "name": self.lyceum.name,
                }
            ],
        )
        self.assertNotIn(str(inactive_lyceum.id), authenticated_response.content.decode())

    def test_verified_active_permission_rejects_anonymous_unverified_and_suspended_users(self) -> None:
        permission = IsVerifiedActiveStudent()
        factory = APIRequestFactory()

        anonymous_request = factory.get("/")
        anonymous_request.user = AnonymousUser()
        self.assertFalse(permission.has_permission(anonymous_request, None))

        unverified_request = factory.get("/")
        unverified_request.user = self.user
        self.assertFalse(permission.has_permission(unverified_request, None))

        self.create_record(external_student_key="student-011")
        self.assertEqual(self.claim(self.user).status_code, 200)
        self.user.refresh_from_db()
        verified_request = factory.get("/")
        verified_request.user = self.user
        self.assertTrue(permission.has_permission(verified_request, None))

        self.user.status = AccountStatus.SUSPENDED
        self.user.save(update_fields=("status", "updated_at"))
        suspended_request = factory.get("/")
        suspended_request.user = self.user
        self.assertFalse(permission.has_permission(suspended_request, None))

    def test_verification_attempts_are_throttled_per_authenticated_account(self) -> None:
        rest_framework_settings = {
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {
                "telegram_auth": "20/hour",
                "student_verification": "5/hour",
            },
        }
        with self.settings(REST_FRAMEWORK=rest_framework_settings):
            cache.clear()
            for _ in range(5):
                response = self.claim(self.user, group="wrong-group")
                self.assertEqual(response.status_code, 400)

            throttled_response = self.claim(self.user, group="wrong-group")

        self.assertEqual(throttled_response.status_code, 429)
        self.assertEqual(throttled_response.json()["error"]["code"], "THROTTLED")
