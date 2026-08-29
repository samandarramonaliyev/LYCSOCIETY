from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.identity.models import User

from .models import StudentProfile


@receiver(post_save, sender=User)
def create_student_profile(
    sender,
    instance: User,
    created: bool,
    **kwargs,
) -> None:  # type: ignore[no-untyped-def]
    if created:
        StudentProfile.objects.get_or_create(user=instance)
