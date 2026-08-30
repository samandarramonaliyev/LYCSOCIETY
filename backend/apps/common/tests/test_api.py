from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from apps.common.api import exception_handler


class HealthCheckApiTests(TestCase):
    def test_health_check_reports_database_readiness(self) -> None:
        response = self.client.get("/api/v1/health/", secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})


class ErrorPrivacyTests(TestCase):
    @patch("apps.common.api.logger")
    def test_unhandled_exception_text_is_not_logged_or_returned(self, logger) -> None:
        response = exception_handler(
            RuntimeError("sensitive provider response https://example.invalid/invite"),
            {},
        )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("sensitive", str(response.data))
        self.assertNotIn("invite", str(response.data))
        logger.error.assert_called_once_with(
            "Unhandled API exception",
            extra={"exception_type": "RuntimeError"},
        )
