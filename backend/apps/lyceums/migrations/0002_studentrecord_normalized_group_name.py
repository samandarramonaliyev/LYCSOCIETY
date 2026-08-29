from __future__ import annotations

from django.db import migrations, models


def populate_normalized_group_names(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
    StudentRecord = apps.get_model("lyceums", "StudentRecord")

    for student_record in StudentRecord.objects.all().iterator():
        student_record.normalized_group_name = " ".join(
            student_record.group_name.strip().split()
        ).casefold()
        student_record.save(update_fields=("normalized_group_name",))


class Migration(migrations.Migration):
    dependencies = [
        ("lyceums", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentrecord",
            name="normalized_group_name",
            field=models.CharField(default="", editable=False, max_length=64),
            preserve_default=False,
        ),
        migrations.RunPython(populate_normalized_group_names, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="studentrecord",
            index=models.Index(
                fields=(
                    "lyceum",
                    "status",
                    "normalized_first_name",
                    "normalized_last_name",
                    "normalized_group_name",
                ),
                name="lyceums_record_match_idx",
            ),
        ),
    ]
