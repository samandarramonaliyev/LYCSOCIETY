from __future__ import annotations

from django.test import TestCase


class HealthCheckApiTests(TestCase):
    def test_health_check_reports_database_readiness(self) -> None:
        response = self.client.get("/api/v1/health/", secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
