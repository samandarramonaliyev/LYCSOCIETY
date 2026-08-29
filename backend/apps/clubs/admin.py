from __future__ import annotations

from django import forms
from django.contrib import admin, messages

from .models import Club, ClubMembership, ClubStatus, JoinRequest, JoinRequestStatus
from .services import ClubStateConflict, moderate_club


class ClubAdminForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == ClubStatus.REJECTED and not str(cleaned.get("rejection_reason", "")).strip():
            self.add_error("rejection_reason", "A rejection reason is required.")
        return cleaned


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    form = ClubAdminForm
    list_display = ("name", "lyceum", "owner", "category", "status", "created_at")
    list_filter = ("status", "category", "lyceum")
    search_fields = ("name", "short_description", "owner__telegram_username", "owner__telegram_user_id")
    filter_horizontal = ("interests",)
    list_select_related = ("lyceum", "owner")
    readonly_fields = ("id", "created_at", "updated_at")
    actions = ("approve_selected", "pause_selected", "archive_selected")

    @admin.action(description="Approve selected pending clubs")
    def approve_selected(self, request, queryset):  # type: ignore[no-untyped-def]
        self._moderate_selected(request, queryset, "approve")

    @admin.action(description="Pause selected active clubs")
    def pause_selected(self, request, queryset):  # type: ignore[no-untyped-def]
        self._moderate_selected(request, queryset, "pause")

    @admin.action(description="Archive selected clubs")
    def archive_selected(self, request, queryset):  # type: ignore[no-untyped-def]
        self._moderate_selected(request, queryset, "archive")

    def _moderate_selected(self, request, queryset, action: str) -> None:  # type: ignore[no-untyped-def]
        changed = 0
        for club in queryset:
            try:
                moderate_club(club_id=club.pk, action=action)
            except ClubStateConflict:
                continue
            changed += 1
        self.message_user(request, f"{changed} club(s) updated.", messages.SUCCESS)


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("club", "user", "role", "status", "joined_at", "left_at")
    list_filter = ("role", "status", "club__lyceum")
    search_fields = ("club__name", "user__telegram_username", "user__telegram_user_id")
    list_select_related = ("club", "club__lyceum", "user")
    readonly_fields = ("id", "created_at", "updated_at", "joined_at")


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("club", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "club__lyceum")
    search_fields = ("club__name", "user__telegram_username", "user__telegram_user_id")
    list_select_related = ("club", "club__lyceum", "user")
    readonly_fields = ("id", "created_at", "updated_at")
