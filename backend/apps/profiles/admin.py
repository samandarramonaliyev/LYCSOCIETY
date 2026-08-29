from __future__ import annotations

from django.contrib import admin

from .models import Interest, StudentProfile


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "verified_lyceum_display", "verified_group_display", "updated_at")
    search_fields = (
        "user__telegram_user_id",
        "user__telegram_username",
        "user__telegram_first_name",
        "user__telegram_last_name",
    )
    list_select_related = ("user", "user__student_record", "user__student_record__lyceum")
    filter_horizontal = ("interests",)
    readonly_fields = (
        "id",
        "official_student_record",
        "verified_lyceum_display",
        "verified_group_display",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Account", {"fields": ("user", "official_student_record")} ),
        ("Verified data", {"fields": ("verified_lyceum_display", "verified_group_display")} ),
        ("Editable profile", {"fields": ("about", "hobbies", "profile_photo_url", "interests")} ),
        ("Audit", {"fields": ("id", "created_at", "updated_at")} ),
    )

    @admin.display(description="Verified lyceum")
    def verified_lyceum_display(self, profile: StudentProfile) -> str:
        return str(profile.verified_lyceum) if profile.verified_lyceum else "Unverified"

    @admin.display(description="Verified group")
    def verified_group_display(self, profile: StudentProfile) -> str:
        return profile.verified_group_name or "Unverified"
