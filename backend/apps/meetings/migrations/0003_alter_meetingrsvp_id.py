import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("meetings", "0002_meeting_rsvp_unique")]

    operations = [
        migrations.AlterField(
            model_name="meetingrsvp",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
