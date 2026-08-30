from __future__ import annotations

from urllib.parse import urlparse

from django.db import transaction
from rest_framework import serializers

from .models import Interest, StudentProfile


MAX_PROFILE_INTERESTS = 10
_MAX_SUBMITTED_INTEREST_IDS = 50
_IMMUTABLE_FIELDS = {
    "first_name",
    "last_name",
    "group",
    "group_name",
    "lyceum",
    "lyceum_id",
    "official_student_record",
    "official_student_record_id",
}


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ("id", "name", "slug")
        read_only_fields = fields


class SelfProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    lyceum = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    interests = serializers.SerializerMethodField()
    interest_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        allow_empty=True,
        max_length=_MAX_SUBMITTED_INTEREST_IDS,
    )

    class Meta:
        model = StudentProfile
        fields = (
            "first_name",
            "last_name",
            "lyceum",
            "group",
            "about",
            "hobbies",
            "profile_photo_url",
            "interests",
            "interest_ids",
        )
        read_only_fields = ("first_name", "last_name", "lyceum", "group", "interests")

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        submitted = set(self.initial_data) if isinstance(self.initial_data, dict) else set()
        forbidden = sorted(submitted & _IMMUTABLE_FIELDS)
        if forbidden:
            raise serializers.ValidationError(
                {field: "This verified field is read-only." for field in forbidden}
            )
        allowed = {"about", "hobbies", "profile_photo_url", "interest_ids"}
        unexpected = sorted(submitted - allowed)
        if unexpected:
            raise serializers.ValidationError(
                {field: "This field is not writable." for field in unexpected}
            )

        if "about" in attrs:
            attrs["about"] = str(attrs["about"]).strip()
        if "hobbies" in attrs:
            attrs["hobbies"] = " ".join(str(attrs["hobbies"]).strip().split())
        if "profile_photo_url" in attrs:
            photo_url = str(attrs["profile_photo_url"]).strip()
            attrs["profile_photo_url"] = photo_url
            if photo_url:
                parsed = urlparse(photo_url)
                if (
                    parsed.scheme.lower() != "https"
                    or not parsed.netloc
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    raise serializers.ValidationError(
                        {"profile_photo_url": "A valid HTTPS URL is required."}
                    )

        if "interest_ids" in attrs:
            raw_ids = attrs["interest_ids"]
            unique_ids: list[object] = []
            seen: set[object] = set()
            for interest_id in raw_ids:  # type: ignore[union-attr]
                if interest_id not in seen:
                    seen.add(interest_id)
                    unique_ids.append(interest_id)
            if len(unique_ids) > MAX_PROFILE_INTERESTS:
                raise serializers.ValidationError(
                    {"interest_ids": f"Select no more than {MAX_PROFILE_INTERESTS} interests."}
                )
            interests = list(
                Interest.objects.filter(pk__in=unique_ids, is_active=True)
            )
            if len(interests) != len(unique_ids):
                raise serializers.ValidationError(
                    {"interest_ids": "One or more selected interests are unavailable."}
                )
            attrs["interest_ids"] = unique_ids
        return attrs

    def get_first_name(self, obj: StudentProfile) -> str | None:
        record = obj.official_student_record
        return record.first_name if record else None

    def get_last_name(self, obj: StudentProfile) -> str | None:
        record = obj.official_student_record
        return record.last_name if record else None

    def get_lyceum(self, obj: StudentProfile) -> dict[str, str] | None:
        lyceum = obj.verified_lyceum
        if lyceum is None:
            return None
        return {"id": str(lyceum.id), "name": lyceum.name}

    def get_group(self, obj: StudentProfile) -> str | None:
        return obj.verified_group_name

    def get_interests(self, obj: StudentProfile) -> list[dict[str, object]]:
        return InterestSerializer(
            [interest for interest in obj.interests.all() if interest.is_active],
            many=True,
        ).data

    def update(self, instance: StudentProfile, validated_data: dict[str, object]) -> StudentProfile:
        interest_ids = validated_data.pop("interest_ids", None)
        with transaction.atomic():
            profile = StudentProfile.objects.select_for_update().get(pk=instance.pk)
            changed_fields: list[str] = []
            for field in ("about", "hobbies", "profile_photo_url"):
                if field in validated_data:
                    setattr(profile, field, validated_data[field])
                    changed_fields.append(field)
            if changed_fields:
                profile.save(update_fields=(*changed_fields, "updated_at"))
            if interest_ids is not None:
                locked_interests = list(
                    Interest.objects.select_for_update().filter(pk__in=interest_ids)
                )
                if len(locked_interests) != len(interest_ids) or any(
                    not interest.is_active for interest in locked_interests
                ):
                    raise serializers.ValidationError(
                        {"interest_ids": "One or more selected interests are unavailable."}
                    )
                profile.interests.set(locked_interests)
        return profile
