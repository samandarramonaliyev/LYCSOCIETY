from django.test import TestCase
from django.contrib import admin
from apps.reports.models import Report
from apps.reports.admin import ReportAdmin
class ReportAdminTests(TestCase):
    def test_report_is_registered(self): self.assertIsInstance(admin.site._registry[Report], ReportAdmin)
