from __future__ import annotations

from rest_framework import serializers

from .models import Announcement, Meeting, MeetingRSVP


class RejectUnknownFieldsMixin:
    writable_field_names: frozenset[str]

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        submitted = set(self.initial_data) if isinstance(self.initial_data, dict) else set()
        unexpected = sorted(submitted - self.writable_field_names)
        if unexpected:
            raise serializers.ValidationError(
                {field: "This field is not writable." for field in unexpected}
            )
        return super().validate(attrs)


class MeetingSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    writable_field_names = frozenset({"title", "description", "starts_at", "location"})

    class Meta:
        model = Meeting
        fields = (
            "id",
            "title",
            "description",
            "starts_at",
            "location",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")


class AnnouncementSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    writable_field_names = frozenset({"title", "message"})

    class Meta:
        model = Announcement
        fields = ("id", "title", "message", "created_at")
        read_only_fields = ("id", "created_at")


class RSVPSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    writable_field_names = frozenset({"response"})

    class Meta:
        model = MeetingRSVP
        fields = ("response",)
