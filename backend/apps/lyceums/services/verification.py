from __future__ import annotations

from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.identity.exceptions import AccountUnavailable, AlreadyVerified, VerificationClaimFailed
from apps.identity.models import User
from apps.lyceums.models import Lyceum, LyceumStatus, StudentRecord, StudentRecordStatus, normalize_text
from apps.profiles.models import StudentProfile


def claim_student_record(
    *,
    user: User,
    lyceum_id: UUID,
    first_name: str,
    last_name: str,
    group_name: str,
) -> StudentRecord:
    """Atomically claim one exact active roster match for an active account."""

    normalized_first_name = normalize_text(first_name)
    normalized_last_name = normalize_text(last_name)
    normalized_group_name = normalize_text(group_name)

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if not locked_user.is_active:
            raise AccountUnavailable

        if StudentRecord.objects.filter(verified_user_id=locked_user.pk).exists():
            raise AlreadyVerified

        lyceum = (
            Lyceum.objects.select_for_update()
            .filter(pk=lyceum_id, status=LyceumStatus.ACTIVE)
            .first()
        )
        if lyceum is None:
            raise VerificationClaimFailed

        candidates = list(
            StudentRecord.objects.select_for_update()
            .select_related("lyceum")
            .filter(
                lyceum=lyceum,
                status=StudentRecordStatus.ACTIVE,
                normalized_first_name=normalized_first_name,
                normalized_last_name=normalized_last_name,
                normalized_group_name=normalized_group_name,
            )
        )
        if len(candidates) != 1 or candidates[0].verified_user_id is not None:
            raise VerificationClaimFailed

        student_record = candidates[0]
        student_record.verified_user = locked_user
        student_record.verified_at = timezone.now()
        student_record.save(update_fields=("verified_user", "verified_at", "updated_at"))
        StudentProfile.objects.get_or_create(user=locked_user)

    return student_record
