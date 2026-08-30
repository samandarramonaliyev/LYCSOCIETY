from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import Lyceum, StudentRecord


@admin.register(Lyceum)
class LyceumAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "code", "city")
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(StudentRecord)
class StudentRecordAdmin(admin.ModelAdmin):
    actions = ("reset_verification_claims",)
    list_display = (
        "last_name",
        "first_name",
        "group_name",
        "lyceum",
        "status",
        "claim_state",
        "updated_at",
    )
    list_filter = ("status", "lyceum")
    search_fields = (
        "external_student_key",
        "first_name",
        "last_name",
        "group_name",
        "lyceum__code",
        "lyceum__name",
    )
    list_select_related = ("lyceum", "verified_user")
    ordering = ("lyceum__name", "last_name", "first_name")
    readonly_fields = (
        "id",
        "normalized_first_name",
        "normalized_last_name",
        "normalized_group_name",
        "verification_attempts",
        "verified_user",
        "verified_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Official record",
            {
                "fields": (
                    "lyceum",
                    "external_student_key",
                    "first_name",
                    "last_name",
                    "group_name",
                    "status",
                )
            },
        ),
        (
            "Matching metadata",
            {
                "fields": (
                    "normalized_first_name",
                    "normalized_last_name",
                    "normalized_group_name",
                )
            },
        ),
        (
            "Verification state",
            {
                "fields": (
                    "verified_user",
                    "verified_at",
                    "verification_attempts",
                    "verification_code_expires_at",
                )
            },
        ),
        ("Audit", {"fields": ("id", "created_at", "updated_at")} ),
    )

    def get_readonly_fields(self, request, obj=None):  # type: ignore[no-untyped-def]
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.is_claimed:
            readonly_fields.extend(
                (
                    "lyceum",
                    "external_student_key",
                    "first_name",
                    "last_name",
                    "group_name",
                )
            )
        return readonly_fields

    @admin.display(boolean=True, description="Claimed")
    def claim_state(self, student_record: StudentRecord) -> bool:
        return student_record.is_claimed

    @admin.action(description="Reset verification claims for selected official records")
    def reset_verification_claims(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        record_ids = list(
            queryset.filter(verified_user__isnull=False).values_list("pk", flat=True)
        )
        with transaction.atomic():
            reset_count = queryset.filter(verified_user__isnull=False).update(
                verified_user=None,
                verified_at=None,
                updated_at=timezone.now(),
            )
            if record_ids:
                LogEntry.objects.log_actions(
                    request.user.pk,
                    StudentRecord.objects.filter(pk__in=record_ids),
                    CHANGE,
                    change_message="Reset verification claim.",
                )
        self.message_user(
            request,
            f"Reset {reset_count} verification claim(s).",
            level=messages.WARNING,
        )
