# Generated manually for the Phase 1 foundation. Verify with Django makemigrations --check.

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE
from django.db.models.functions import Lower

import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Interest",
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
                ("name", models.CharField(max_length=80)),
                ("slug", models.SlugField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="StudentProfile",
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
                ("about", models.TextField(blank=True, max_length=1000)),
                ("hobbies", models.CharField(blank=True, max_length=500)),
                ("profile_photo_url", models.URLField(blank=True, max_length=500)),
                (
                    "interests",
                    models.ManyToManyField(
                        blank=True,
                        related_name="profiles",
                        to="profiles.interest",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("user__telegram_user_id",)},
        ),
        migrations.AddConstraint(
            model_name="interest",
            constraint=models.UniqueConstraint(
                Lower("name"),
                name="profiles_interest_name_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="interest",
            constraint=models.UniqueConstraint(
                Lower("slug"),
                name="profiles_interest_slug_ci_unique",
            ),
        ),
    ]
