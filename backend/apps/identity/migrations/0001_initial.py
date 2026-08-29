# Generated manually for the Phase 1 foundation. Verify with Django makemigrations --check.

import uuid

import apps.identity.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Designates that this user has all permissions without explicitly "
                            "assigning them."
                        ),
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "telegram_user_id",
                    models.PositiveBigIntegerField(
                        help_text=(
                            "Telegram numeric user ID. This is the account identity, not a "
                            "display field."
                        ),
                        unique=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("telegram_username", models.CharField(blank=True, max_length=128)),
                ("telegram_first_name", models.CharField(blank=True, max_length=128)),
                ("telegram_last_name", models.CharField(blank=True, max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("SUSPENDED", "Suspended"),
                            ("DEACTIVATED", "Deactivated"),
                        ],
                        db_index=True,
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("is_staff", models.BooleanField(default=False)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "The groups this user belongs to. A user will get all permissions "
                            "granted to each of their groups."
                        ),
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "ordering": ("telegram_user_id",),
            },
            managers=[
                ("objects", apps.identity.models.UserManager()),
            ],
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(("telegram_user_id__gt", 0)),
                name="identity_user_telegram_id_positive",
            ),
        ),
    ]
