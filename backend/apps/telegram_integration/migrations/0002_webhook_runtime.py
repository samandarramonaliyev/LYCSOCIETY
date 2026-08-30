from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def bind_existing_challenge_owners(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
    Challenge = apps.get_model("telegram_integration", "TelegramLinkChallenge")
    for challenge in Challenge.objects.select_related("club").iterator():
        challenge.expected_owner_id = challenge.club.owner_id
        challenge.save(update_fields=("expected_owner",))


class Migration(migrations.Migration):
    dependencies = [
        ("telegram_integration", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramlinkchallenge",
            name="expected_owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="telegram_link_challenges",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(bind_existing_challenge_owners, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="telegramlinkchallenge",
            name="expected_owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="telegram_link_challenges",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="TelegramWebhookUpdate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("update_id", models.PositiveBigIntegerField(unique=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
