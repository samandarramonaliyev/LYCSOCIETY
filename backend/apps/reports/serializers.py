from __future__ import annotations

from rest_framework import serializers

from .models import ReportReason


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=("CLUB", "ANNOUNCEMENT"))
    target_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=ReportReason.choices)
    details = serializers.CharField(max_length=1_000, required=False, allow_blank=True)

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        submitted = set(self.initial_data) if isinstance(self.initial_data, dict) else set()
        unexpected = sorted(submitted - set(self.fields))
        if unexpected:
            raise serializers.ValidationError(
                {field: "This field is not writable." for field in unexpected}
            )
        if attrs["reason"] == ReportReason.OTHER and not attrs.get("details", "").strip():
            raise serializers.ValidationError(
                {"details": "Details are required for OTHER."}
            )
        attrs["details"] = attrs.get("details", "").strip()
        return attrs
