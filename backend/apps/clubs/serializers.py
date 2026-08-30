from __future__ import annotations

from rest_framework import serializers

from apps.profiles.serializers import InterestSerializer

from .models import Club, ClubCategory, ClubMembership, JoinRequest


class ClubWriteSerializer(serializers.ModelSerializer):
    interest_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True, max_length=50, write_only=True
    )

    class Meta:
        model = Club
        fields = ("name", "short_description", "description", "category", "interest_ids")

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        incoming = set(self.initial_data) if isinstance(self.initial_data, dict) else set()
        allowed = set(self.fields)
        unknown = sorted(incoming - allowed)
        if unknown:
            raise serializers.ValidationError({field: "This field is not writable." for field in unknown})
        category = attrs.get("category")
        if category is not None and category not in ClubCategory.values:
            raise serializers.ValidationError({"category": "Choose a valid club category."})
        if "interest_ids" in attrs:
            ids = list(dict.fromkeys(attrs["interest_ids"]))  # type: ignore[arg-type]
            if len(ids) > 10:
                raise serializers.ValidationError({"interest_ids": "Select no more than 10 interests."})
            attrs["interest_ids"] = ids
        for field in ("name", "short_description", "description"):
            if field in attrs:
                attrs[field] = str(attrs[field]).strip()
                if not attrs[field]:
                    raise serializers.ValidationError({field: "This field may not be blank."})
        return attrs


def _public_user(user) -> dict[str, object]:  # type: ignore[no-untyped-def]
    record = getattr(user, "student_record", None)
    profile = getattr(user, "profile", None)
    return {
        "first_name": record.first_name if record else "",
        "last_name": record.last_name if record else "",
        "about": profile.about if profile else "",
        "profile_photo_url": profile.profile_photo_url if profile else "",
        "interests": InterestSerializer(
            [interest for interest in profile.interests.all() if interest.is_active], many=True
        ).data
        if profile
        else [],
    }


class ClubSerializer(serializers.ModelSerializer):
    interests = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()
    request_status = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = (
            "id", "name", "short_description", "description", "category", "interests", "owner",
            "member_count", "membership_status", "request_status", "request_id", "created_at",
        )

    def get_interests(self, obj: Club):
        return InterestSerializer(obj.interests.filter(is_active=True), many=True).data

    def get_owner(self, obj: Club):
        return _public_user(obj.owner)

    def get_member_count(self, obj: Club) -> int:
        return obj.memberships.filter(status="ACTIVE").count()

    def get_membership_status(self, obj: Club) -> str | None:
        user = self.context.get("request").user if self.context.get("request") else None
        membership = obj.memberships.filter(user=user, status="ACTIVE").first() if user else None
        return membership.role if membership else None

    def get_request_status(self, obj: Club) -> str | None:
        user = self.context.get("request").user if self.context.get("request") else None
        request = obj.join_requests.filter(user=user).order_by("-created_at").first() if user else None
        return request.status if request else None

    def get_request_id(self, obj: Club) -> str | None:
        user = self.context.get("request").user if self.context.get("request") else None
        join_request = (
            obj.join_requests.filter(user=user).order_by("-created_at").first()
            if user
            else None
        )
        return str(join_request.pk) if join_request else None


class OwnerClubSerializer(ClubSerializer):
    class Meta(ClubSerializer.Meta):
        fields = ClubSerializer.Meta.fields + ("status", "rejection_reason")


class JoinRequestSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()

    class Meta:
        model = JoinRequest
        fields = ("id", "status", "rejection_reason", "student", "created_at", "updated_at")
        read_only_fields = fields

    def get_student(self, obj: JoinRequest):
        record = getattr(obj.user, "student_record", None)
        profile = getattr(obj.user, "profile", None)
        return {
            "first_name": record.first_name if record else "",
            "last_name": record.last_name if record else "",
            "group": record.group_name if record else "",
            "about": profile.about if profile else "",
            "profile_photo_url": profile.profile_photo_url if profile else "",
            "interests": InterestSerializer(
                [i for i in profile.interests.all() if i.is_active], many=True
            ).data
            if profile
            else [],
        }


class JoinRequestDecisionSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=1_000, required=False, allow_blank=True)


class MemberSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()

    class Meta:
        model = ClubMembership
        fields = ("id", "role", "joined_at", "student")
        read_only_fields = fields

    def get_student(self, obj: ClubMembership):
        record = getattr(obj.user, "student_record", None)
        profile = getattr(obj.user, "profile", None)
        return {
            "first_name": record.first_name if record else "",
            "last_name": record.last_name if record else "",
            "group": record.group_name if record else "",
            "profile_photo_url": profile.profile_photo_url if profile else "",
            "interests": InterestSerializer(
                [i for i in profile.interests.all() if i.is_active], many=True
            ).data
            if profile
            else [],
        }
