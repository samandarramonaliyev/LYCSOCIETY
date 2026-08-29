from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsVerifiedActiveStudent(BasePermission):
    """Foundation permission for future student-facing API routes."""

    message = "A verified active student account is required."

    def has_permission(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "can_access_student_features", False)
        )
