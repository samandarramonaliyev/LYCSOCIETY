from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("meetings", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="meetingrsvp",
            constraint=models.UniqueConstraint(
                fields=("meeting", "user"),
                name="meetings_rsvp_unique",
            ),
        ),
    ]
