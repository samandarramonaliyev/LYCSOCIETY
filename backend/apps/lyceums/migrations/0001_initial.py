# Generated manually for the Phase 1 foundation. Verify with Django makemigrations --check.

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import PROTECT
from django.db.models.functions import Lower

import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Lyceum",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "code",
                    models.SlugField(
                        help_text="Stable internal lyceum code. Stored in lowercase.",
                        max_length=50,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("city", models.CharField(blank=True, max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        db_index=True,
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
            ],
            options={
                "ordering": ("name", "code"),
            },
        ),
        migrations.CreateModel(
            name="StudentRecord",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "external_student_key",
                    models.CharField(
                        blank=True,
                        help_text="Administration-provided stable identifier, if available.",
                        max_length=128,
                        null=True,
                    ),
                ),
                ("first_name", models.CharField(max_length=128)),
                ("last_name", models.CharField(max_length=128)),
                ("normalized_first_name", models.CharField(editable=False, max_length=128)),
                ("normalized_last_name", models.CharField(editable=False, max_length=128)),
                ("group_name", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        db_index=True,
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                (
                    "verification_code_hash",
                    models.CharField(blank=True, editable=False, max_length=256),
                ),
                ("verification_code_expires_at", models.DateTimeField(blank=True, null=True)),
                ("verification_attempts", models.PositiveSmallIntegerField(default=0)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "lyceum",
                    models.ForeignKey(
                        on_delete=PROTECT,
                        related_name="student_records",
                        to="lyceums.lyceum",
                    ),
                ),
                (
                    "verified_user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=PROTECT,
                        related_name="student_record",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("lyceum__name", "last_name", "first_name", "group_name"),
            },
        ),
        migrations.AddConstraint(
            model_name="lyceum",
            constraint=models.UniqueConstraint(Lower("code"), name="lyceums_lyceum_code_ci_unique"),
        ),
        migrations.AddConstraint(
            model_name="studentrecord",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_student_key__isnull", False)),
                fields=("lyceum", "external_student_key"),
                name="lyceums_student_record_external_key_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentrecord",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("verified_at__isnull", True), ("verified_user__isnull", True))
                    | models.Q(("verified_at__isnull", False), ("verified_user__isnull", False))
                ),
                name="lyceums_record_verified_pair_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentrecord",
            constraint=models.CheckConstraint(
                condition=models.Q(("verification_attempts__gte", 0)),
                name="lyceums_record_verification_attempts_nonnegative",
            ),
        ),
        migrations.AddIndex(
            model_name="studentrecord",
            index=models.Index(
                fields=["lyceum", "status", "group_name"],
                name="lyceums_record_scope_group_idx",
            ),
        ),
    ]
