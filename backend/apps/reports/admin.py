from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.db import transaction
from django.utils import timezone

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("target_type", "target_id", "reason", "status", "reporter", "created_at", "reviewed_by")
    list_filter = ("status", "reason")
    search_fields = (
        "club__name",
        "announcement__title",
        "reporter__telegram_user_id",
        "details",
    )
    readonly_fields = (
        "id",
        "reporter",
        "club",
        "announcement",
        "created_at",
        "updated_at",
    )
    actions = ("mark_reviewed", "mark_actioned", "dismiss")

    def _mark(self, request, queryset, status_value) -> None:  # type: ignore[no-untyped-def]
        with transaction.atomic():
            report_ids = list(queryset.values_list("pk", flat=True))
            queryset.update(
                status=status_value,
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
                updated_at=timezone.now(),
            )
            if report_ids:
                LogEntry.objects.log_actions(
                    request.user.pk,
                    Report.objects.filter(pk__in=report_ids),
                    CHANGE,
                    change_message=f"Report status changed to {status_value}.",
                )

    @admin.action(description="Mark selected reports reviewed")
    def mark_reviewed(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        self._mark(request, queryset, "REVIEWED")

    @admin.action(description="Mark selected reports actioned")
    def mark_actioned(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        self._mark(request, queryset, "ACTIONED")

    @admin.action(description="Dismiss selected reports")
    def dismiss(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        self._mark(request, queryset, "DISMISSED")
