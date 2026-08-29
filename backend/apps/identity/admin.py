from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    list_display = (
        "telegram_user_id",
        "display_name",
        "status",
        "is_staff",
        "verification_state",
        "created_at",
    )
    list_filter = ("status", "is_staff", "is_superuser")
    search_fields = (
        "telegram_user_id",
        "telegram_username",
        "telegram_first_name",
        "telegram_last_name",
    )
    ordering = ("telegram_user_id",)
    readonly_fields = (
        "id",
        "last_seen_at",
        "created_at",
        "updated_at",
        "verification_state",
    )
    fieldsets = (
        (None, {"fields": ("telegram_user_id", "password")}),
        (
            "Telegram display metadata",
            {
                "fields": (
                    "telegram_username",
                    "telegram_first_name",
                    "telegram_last_name",
                )
            },
        ),
        ("Account state", {"fields": ("status", "last_seen_at", "verification_state")} ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Audit", {"fields": ("id", "created_at", "updated_at")} ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "telegram_user_id",
                    "telegram_username",
                    "telegram_first_name",
                    "telegram_last_name",
                    "status",
                    "is_staff",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    def get_queryset(self, request):  # type: ignore[no-untyped-def]
        return super().get_queryset(request).select_related("student_record")

    def get_readonly_fields(self, request, obj=None):  # type: ignore[no-untyped-def]
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.append("telegram_user_id")
        return readonly_fields

    @admin.display(description="Name")
    def display_name(self, user: User) -> str:
        return user.get_full_name() or "—"

    @admin.display(boolean=True, description="Verified", ordering="student_record__status")
    def verification_state(self, user: User) -> bool:
        return user.is_verified
