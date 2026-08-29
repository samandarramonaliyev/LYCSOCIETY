from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT
from django.db.models import Q
from django.utils import timezone
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("lyceums", "0002_studentrecord_normalized_group_name"),
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Club",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("short_description", models.CharField(max_length=280)),
                ("description", models.TextField(max_length=5000)),
                ("category", models.CharField(choices=[("TECHNOLOGY", "Technology"), ("SCIENCE", "Science"), ("BUSINESS", "Business"), ("SPORTS", "Sports"), ("ARTS", "Arts"), ("LANGUAGES", "Languages"), ("ACADEMIC", "Academic"), ("SOCIAL", "Social"), ("OTHER", "Other")], max_length=16)),
                ("status", models.CharField(choices=[("PENDING", "Pending review"), ("ACTIVE", "Active"), ("REJECTED", "Rejected"), ("PAUSED", "Paused"), ("ARCHIVED", "Archived")], db_index=True, default="PENDING", max_length=16)),
                ("rejection_reason", models.TextField(blank=True, max_length=1000)),
                ("interests", models.ManyToManyField(blank=True, related_name="clubs", to="profiles.interest")),
                ("lyceum", models.ForeignKey(on_delete=PROTECT, related_name="clubs", to="lyceums.lyceum")),
                ("owner", models.ForeignKey(on_delete=PROTECT, related_name="owned_clubs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "name")},
        ),
        migrations.CreateModel(
            name="ClubMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("MEMBER", "Member")], max_length=16)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("REMOVED", "Removed")], db_index=True, default="ACTIVE", max_length=16)),
                ("joined_at", models.DateTimeField(default=timezone.now)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("club", models.ForeignKey(on_delete=CASCADE, related_name="memberships", to="clubs.club")),
                ("user", models.ForeignKey(on_delete=PROTECT, related_name="club_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("joined_at", "created_at")},
        ),
        migrations.CreateModel(
            name="JoinRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="PENDING", max_length=16)),
                ("rejection_reason", models.TextField(blank=True, max_length=1000)),
                ("club", models.ForeignKey(on_delete=CASCADE, related_name="join_requests", to="clubs.club")),
                ("user", models.ForeignKey(on_delete=PROTECT, related_name="club_join_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(model_name="club", constraint=models.UniqueConstraint(fields=("owner",), name="clubs_one_per_owner")),
        migrations.AddConstraint(model_name="club", constraint=models.CheckConstraint(condition=Q(status="REJECTED", rejection_reason__gt="") | ~Q(status="REJECTED"), name="clubs_rejected_requires_reason")),
        migrations.AddConstraint(model_name="clubmembership", constraint=models.UniqueConstraint(condition=Q(status="ACTIVE"), fields=("club", "user"), name="clubs_active_membership_unique")),
        migrations.AddConstraint(model_name="clubmembership", constraint=models.UniqueConstraint(condition=Q(role="OWNER", status="ACTIVE"), fields=("club",), name="clubs_one_owner_membership")),
        migrations.AddConstraint(model_name="clubmembership", constraint=models.CheckConstraint(condition=Q(status="ACTIVE", left_at__isnull=True) | Q(status="REMOVED", left_at__isnull=False), name="clubs_membership_status_left_consistent")),
        migrations.AddConstraint(model_name="joinrequest", constraint=models.UniqueConstraint(condition=Q(status="PENDING"), fields=("club", "user"), name="clubs_pending_join_request_unique")),
    ]
