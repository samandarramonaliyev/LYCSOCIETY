from django.db import migrations, models
import django.db.models.deletion


def copy_typed_targets(apps, schema_editor):  # type: ignore[no-untyped-def]
    Report = apps.get_model("reports", "Report")
    Club = apps.get_model("clubs", "Club")
    Announcement = apps.get_model("meetings", "Announcement")
    for report in Report.objects.all().iterator():
        if report.target_type == "CLUB" and Club.objects.filter(pk=report.target_id).exists():
            report.club_id = report.target_id
            report.save(update_fields=("club",))
        elif (
            report.target_type == "ANNOUNCEMENT"
            and Announcement.objects.filter(pk=report.target_id).exists()
        ):
            report.announcement_id = report.target_id
            report.save(update_fields=("announcement",))
        else:
            raise RuntimeError(
                "Cannot migrate a report whose target is missing or unsupported."
            )


def restore_generic_targets(apps, schema_editor):  # type: ignore[no-untyped-def]
    Report = apps.get_model("reports", "Report")
    for report in Report.objects.all().iterator():
        if report.club_id:
            report.target_type = "CLUB"
            report.target_id = report.club_id
        else:
            report.target_type = "ANNOUNCEMENT"
            report.target_id = report.announcement_id
        report.save(update_fields=("target_type", "target_id"))


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0002_meeting_rsvp_unique"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="club",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reports",
                to="clubs.club",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="announcement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reports",
                to="meetings.announcement",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_type",
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_id",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(copy_typed_targets, restore_generic_targets),
        migrations.RemoveConstraint(
            model_name="report",
            name="reports_one_open_per_target",
        ),
        migrations.RemoveField(model_name="report", name="target_type"),
        migrations.RemoveField(model_name="report", name="target_id"),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(announcement__isnull=True, club__isnull=False)
                    | models.Q(announcement__isnull=False, club__isnull=True)
                ),
                name="reports_exactly_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.UniqueConstraint(
                condition=models.Q(club__isnull=False, status="OPEN"),
                fields=("reporter", "club"),
                name="reports_one_open_per_club",
            ),
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.UniqueConstraint(
                condition=models.Q(announcement__isnull=False, status="OPEN"),
                fields=("reporter", "announcement"),
                name="reports_one_open_per_announcement",
            ),
        ),
    ]
