from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.test import TestCase

from apps.clubs.models import Club, ClubStatus
from apps.identity.models import User
from apps.lyceums.models import Lyceum
from apps.reports.models import Report, ReportReason, ReportStatus
from apps.reports.admin import ReportAdmin


class ReportAdminTests(TestCase):
    def test_report_is_registered(self):
        self.assertIsInstance(admin.site._registry[Report], ReportAdmin)

    def test_status_action_records_staff_log_entry(self):
        staff = User.objects.create_user(
            telegram_user_id=990_001,
            is_staff=True,
        )
        reporter = User.objects.create_user(telegram_user_id=990_002)
        lyceum = Lyceum.objects.create(name="Admin Audit Lyceum", code="admin-audit")
        club = Club.objects.create(
            lyceum=lyceum,
            owner=reporter,
            name="Audited Club",
            short_description="Short",
            description="Description",
            category="OTHER",
            status=ClubStatus.ACTIVE,
        )
        report = Report.objects.create(
            reporter=reporter,
            club=club,
            reason=ReportReason.SPAM,
        )
        request = type("Request", (), {"user": staff})()

        ReportAdmin(Report, admin.site)._mark(
            request,
            Report.objects.filter(pk=report.pk),
            ReportStatus.REVIEWED,
        )

        report.refresh_from_db()
        self.assertEqual(report.status, ReportStatus.REVIEWED)
        self.assertEqual(report.reviewed_by_id, staff.pk)
        self.assertTrue(
            LogEntry.objects.filter(
                user_id=staff.pk,
                content_type__model="report",
                object_id=str(report.pk),
            ).exists()
        )
