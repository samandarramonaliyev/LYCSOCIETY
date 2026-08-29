from __future__ import annotations

from django.contrib import admin

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

    @admin.display(boolean=True, description="Claimed")
    def claim_state(self, student_record: StudentRecord) -> bool:
        return student_record.is_claimed
