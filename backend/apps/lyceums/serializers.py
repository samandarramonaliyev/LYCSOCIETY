from __future__ import annotations

from rest_framework import serializers

from apps.lyceums.models import normalize_text


class VerificationClaimSerializer(serializers.Serializer):
    lyceum_id = serializers.UUIDField()
    first_name = serializers.CharField(max_length=128, trim_whitespace=False)
    last_name = serializers.CharField(max_length=128, trim_whitespace=False)
    group = serializers.CharField(max_length=64, trim_whitespace=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        unexpected_fields = set(self.initial_data) - set(self.fields)
        if unexpected_fields:
            raise serializers.ValidationError("Unexpected verification fields.")
        return attrs

    def validate_first_name(self, value: str) -> str:
        return self._validate_matching_value(value)

    def validate_last_name(self, value: str) -> str:
        return self._validate_matching_value(value)

    def validate_group(self, value: str) -> str:
        return self._validate_matching_value(value)

    @staticmethod
    def _validate_matching_value(value: str) -> str:
        if not normalize_text(value):
            raise serializers.ValidationError("This field may not be blank.")
        return value
