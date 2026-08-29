from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.identity.models import AccountStatus, User


class TelegramAuthenticationSerializer(serializers.Serializer):
    init_data = serializers.CharField(
        allow_blank=False,
        max_length=8_192,
        trim_whitespace=False,
    )


def verification_status_for(user: User) -> str:
    if user.status == AccountStatus.SUSPENDED:
        return "SUSPENDED"
    if user.status == AccountStatus.DEACTIVATED:
        return "DEACTIVATED"
    if user.is_verified:
        return "VERIFIED"
    return "UNVERIFIED"


def serialize_account_state(user: User) -> dict[str, object]:
    """Return only self-service account and verified-profile fields."""

    try:
        profile = user.profile
    except ObjectDoesNotExist:
        profile = None

    verified_student: dict[str, object] | None = None
    if user.can_access_student_features:
        try:
            student_record = user.student_record
        except ObjectDoesNotExist:
            student_record = None

        if student_record is not None:
            verified_student = {
                "first_name": student_record.first_name,
                "last_name": student_record.last_name,
                "lyceum": {
                    "id": str(student_record.lyceum_id),
                    "code": student_record.lyceum.code,
                    "name": student_record.lyceum.name,
                },
                "group": student_record.group_name,
            }

    interests: list[dict[str, str]] = []
    if profile is not None:
        interests = [
            {"slug": interest.slug, "name": interest.name}
            for interest in profile.interests.all()
        ]

    return {
        "account_status": user.status,
        "verification_status": verification_status_for(user),
        "can_access_student_features": user.can_access_student_features,
        "telegram": {
            "username": user.telegram_username,
            "first_name": user.telegram_first_name,
            "last_name": user.telegram_last_name,
        },
        "profile": {
            "about": profile.about if profile is not None else "",
            "hobbies": profile.hobbies if profile is not None else "",
            "profile_photo_url": profile.profile_photo_url if profile is not None else "",
            "interests": interests,
        },
        "verified_student": verified_student,
    }
