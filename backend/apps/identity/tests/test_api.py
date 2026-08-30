from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlencode

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework.test import APIClient

from apps.identity.models import AccountStatus, User
from apps.identity.tests.helpers import (
    TEST_BOT_TOKEN,
    build_signed_init_data,
    sign_init_data_values,
)
from apps.lyceums.models import Lyceum, StudentRecord


@override_settings(
    TELEGRAM_BOT_TOKEN=TEST_BOT_TOKEN,
    TELEGRAM_INIT_DATA_MAX_AGE_SECONDS=300,
    TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS=30,
)
class TelegramAuthenticationApiTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self, client: APIClient | None = None) -> str:
        csrf_client = self.client if client is None else client
        response = csrf_client.get("/api/v1/auth/csrf/", secure=True)
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def authenticate(self, init_data: str):
        return self.client.post(
            "/api/v1/auth/telegram/",
            {"init_data": init_data},
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

    def test_valid_signed_init_data_creates_an_authenticated_unverified_user(self) -> None:
        response = self.authenticate(build_signed_init_data(telegram_user_id=610_000_001))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertTrue(response.json()["csrf_token"])
        self.assertEqual(response.json()["user"]["verification_status"], "UNVERIFIED")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().telegram_user_id, 610_000_001)
        self.assertNotIn("telegram_user_id", response.content.decode())

        me_response = self.client.get("/api/v1/auth/me/", secure=True)
        self.assertEqual(me_response.status_code, 200)
        self.assertIsNone(me_response.json()["verified_student"])

    def test_invalid_signature_is_rejected_without_creating_an_account(self) -> None:
        init_data = build_signed_init_data(telegram_user_id=610_000_002)
        tampered_init_data = init_data.replace("student", "attacker", 1)

        response = self.authenticate(tampered_init_data)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Telegram")
        self.assertEqual(response.json()["error"]["code"], "TELEGRAM_INIT_DATA_INVALID")
        self.assertEqual(User.objects.count(), 0)

    def test_tampered_telegram_id_is_rejected(self) -> None:
        init_data = build_signed_init_data(telegram_user_id=610_000_003)
        values = parse_qs(init_data)
        user_data = json.loads(values["user"][0])
        user_data["id"] = 610_099_999
        values["user"] = [json.dumps(user_data, separators=(",", ":"))]
        tampered_init_data = urlencode({key: value[0] for key, value in values.items()})

        response = self.authenticate(tampered_init_data)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "TELEGRAM_INIT_DATA_INVALID")
        self.assertFalse(User.objects.filter(telegram_user_id=610_099_999).exists())

    def test_stale_init_data_is_rejected(self) -> None:
        response = self.authenticate(
            build_signed_init_data(
                telegram_user_id=610_000_004,
                auth_date=int(time.time()) - 301,
            )
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "TELEGRAM_INIT_DATA_EXPIRED")
        self.assertEqual(User.objects.count(), 0)

    def test_reused_fresh_init_data_is_rejected(self) -> None:
        init_data = build_signed_init_data(telegram_user_id=610_000_005)

        self.assertEqual(self.authenticate(init_data).status_code, 200)
        replay_response = self.authenticate(init_data)

        self.assertEqual(replay_response.status_code, 401)
        self.assertEqual(replay_response.json()["error"]["code"], "TELEGRAM_INIT_DATA_REPLAYED")

    def test_same_telegram_identity_updates_metadata_without_creating_a_second_user(self) -> None:
        self.assertEqual(
            self.authenticate(
                build_signed_init_data(
                    telegram_user_id=610_000_006,
                    username="first_username",
                    first_name="First",
                )
            ).status_code,
            200,
        )

        response = self.authenticate(
            build_signed_init_data(
                telegram_user_id=610_000_006,
                username="renamed_username",
                first_name="Updated",
                last_name="Name",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.telegram_username, "renamed_username")
        self.assertEqual(user.telegram_first_name, "Updated")
        self.assertEqual(user.telegram_last_name, "Name")

    def test_frontend_identity_fields_are_rejected_and_never_trusted(self) -> None:
        response = self.client.post(
            "/api/v1/auth/telegram/",
            {
                "init_data": build_signed_init_data(telegram_user_id=610_000_007),
                "telegram_user_id": 999_999_999,
            },
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(telegram_user_id=610_000_007).exists())
        self.assertFalse(User.objects.filter(telegram_user_id=999_999_999).exists())

    def test_suspended_account_does_not_receive_a_session(self) -> None:
        User.objects.create_user(
            telegram_user_id=610_000_008,
            status=AccountStatus.SUSPENDED,
        )

        response = self.authenticate(build_signed_init_data(telegram_user_id=610_000_008))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_UNAVAILABLE")
        self.assertEqual(self.client.get("/api/v1/auth/me/", secure=True).status_code, 403)

    def test_missing_or_malformed_init_data_is_rejected(self) -> None:
        missing_response = self.client.post(
            "/api/v1/auth/telegram/",
            {},
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        malformed_response = self.authenticate("not-a-query-string")

        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(malformed_response.status_code, 401)
        self.assertEqual(malformed_response.json()["error"]["code"], "TELEGRAM_INIT_DATA_INVALID")

    def test_missing_hash_is_rejected(self) -> None:
        init_data = build_signed_init_data(telegram_user_id=610_000_011)
        without_hash = urlencode(
            {
                key: value[0]
                for key, value in parse_qs(init_data).items()
                if key != "hash"
            }
        )

        response = self.authenticate(without_hash)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "TELEGRAM_INIT_DATA_INVALID")

    def test_malformed_and_future_auth_dates_are_rejected(self) -> None:
        user_json = json.dumps({"id": 610_000_012}, separators=(",", ":"))
        malformed = sign_init_data_values({"auth_date": "not-an-integer", "user": user_json})
        future = sign_init_data_values(
            {"auth_date": str(int(time.time()) + 31), "user": user_json}
        )

        malformed_response = self.authenticate(malformed)
        future_response = self.authenticate(future)

        self.assertEqual(malformed_response.status_code, 401)
        self.assertEqual(
            malformed_response.json()["error"]["code"],
            "TELEGRAM_INIT_DATA_INVALID",
        )
        self.assertEqual(future_response.status_code, 401)
        self.assertEqual(
            future_response.json()["error"]["code"],
            "TELEGRAM_INIT_DATA_EXPIRED",
        )

    def test_missing_or_malformed_user_payload_is_rejected(self) -> None:
        now = str(int(time.time()))
        missing = sign_init_data_values({"auth_date": now, "query_id": "missing-user"})
        malformed_json = sign_init_data_values(
            {"auth_date": now, "query_id": "bad-json", "user": "{"}
        )
        non_object_json = sign_init_data_values(
            {"auth_date": now, "query_id": "array-user", "user": "[]"}
        )

        for init_data in (missing, malformed_json, non_object_json):
            response = self.authenticate(init_data)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json()["error"]["code"],
                "TELEGRAM_INIT_DATA_INVALID",
            )

    def test_signed_user_payload_with_invalid_identity_type_is_rejected(self) -> None:
        init_data = sign_init_data_values(
            {
                "auth_date": str(int(time.time())),
                "query_id": "string-id",
                "user": json.dumps({"id": "610000013"}, separators=(",", ":")),
            }
        )

        response = self.authenticate(init_data)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "TELEGRAM_INIT_DATA_INVALID")

    def test_logout_ends_the_session(self) -> None:
        authentication_response = self.authenticate(
            build_signed_init_data(telegram_user_id=610_000_009)
        )
        self.assertEqual(authentication_response.status_code, 200)

        logout_response = self.client.post(
            "/api/v1/auth/logout/",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=authentication_response.json()["csrf_token"],
        )

        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me/", secure=True).status_code, 403)

    def test_session_authenticated_verification_requires_the_returned_csrf_token(self) -> None:
        lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")
        StudentRecord.objects.create(
            lyceum=lyceum,
            external_student_key="student-csrf",
            first_name="Sam",
            last_name="Karimov",
            group_name="10-B",
        )
        csrf_client = APIClient(enforce_csrf_checks=True)
        bootstrap_response = csrf_client.get("/api/v1/auth/csrf/", secure=True)
        self.assertEqual(bootstrap_response.status_code, 200)
        init_data = build_signed_init_data(telegram_user_id=610_000_010)
        missing_login_csrf_response = csrf_client.post(
            "/api/v1/auth/telegram/",
            {"init_data": init_data},
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
        )
        self.assertEqual(missing_login_csrf_response.status_code, 403)
        self.assertEqual(missing_login_csrf_response.json()["error"]["code"], "CSRF_FAILED")
        self.assertFalse(User.objects.filter(telegram_user_id=610_000_010).exists())
        authentication_response = csrf_client.post(
            "/api/v1/auth/telegram/",
            {"init_data": init_data},
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=bootstrap_response.json()["csrf_token"],
        )
        claim_payload = {
            "lyceum_id": str(lyceum.id),
            "first_name": "Sam",
            "last_name": "Karimov",
            "group": "10-B",
        }

        no_csrf_response = csrf_client.post(
            "/api/v1/verification/claim/",
            claim_payload,
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
        )
        csrf_response = csrf_client.post(
            "/api/v1/verification/claim/",
            claim_payload,
            format="json",
            secure=True,
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=authentication_response.json()["csrf_token"],
        )

        self.assertEqual(authentication_response.status_code, 200)
        self.assertEqual(no_csrf_response.status_code, 403)
        self.assertEqual(csrf_response.status_code, 200)
