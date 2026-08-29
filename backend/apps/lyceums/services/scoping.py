from __future__ import annotations

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied

from apps.identity.models import User
from apps.lyceums.models import Lyceum, LyceumStatus, StudentRecord, StudentRecordStatus


class VerifiedLyceumUnavailable(PermissionDenied):
    default_detail = "An active verified lyceum is required."
    default_code = "VERIFIED_LYCEUM_REQUIRED"


def get_verified_lyceum(user: User) -> Lyceum:
    """Resolve the caller's tenant from the trusted active roster binding."""

    if not user.is_authenticated or not user.is_active:
        raise VerifiedLyceumUnavailable

    record = (
        StudentRecord.objects.select_related("lyceum")
        .filter(
            verified_user_id=user.pk,
            status=StudentRecordStatus.ACTIVE,
            lyceum__status=LyceumStatus.ACTIVE,
        )
        .first()
    )
    if record is None:
        raise VerifiedLyceumUnavailable
    return record.lyceum


def scope_queryset_to_verified_lyceum(
    queryset: QuerySet,
    *,
    user: User,
    lyceum_field: str = "lyceum",
) -> QuerySet:
    """Constrain a queryset to the caller's trusted tenant.

    ``Lyceum`` is itself the tenant resource, so it is scoped by primary key.
    Other querysets are expected to expose a foreign-key field named by
    ``lyceum_field`` (or its ``*_id`` variant).
    """

    lyceum = get_verified_lyceum(user)
    if queryset.model is Lyceum:
        return queryset.filter(pk=lyceum.pk)
    value = lyceum.pk if lyceum_field.endswith("_id") else lyceum
    return queryset.filter(**{lyceum_field: value})
