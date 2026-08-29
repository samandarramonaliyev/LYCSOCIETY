from django.conf import settings
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name="Notification", fields=[
            ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ("type",models.CharField(max_length=40,choices=[("CLUB_APPROVED","Club approved"),("CLUB_REJECTED","Club rejected"),("JOIN_REQUEST_CREATED","Join request created"),("JOIN_REQUEST_ACCEPTED","Join request accepted"),("JOIN_REQUEST_REJECTED","Join request rejected"),("MEETING_CREATED","Meeting created"),("MEETING_REMINDER","Meeting reminder"),("ANNOUNCEMENT","Announcement")])),
            ("title",models.CharField(max_length=200)),("body",models.TextField(max_length=2000)),("is_read",models.BooleanField(default=False,db_index=True)),
            ("delivery_status",models.CharField(max_length=10,default="PENDING",choices=[("PENDING","Pending"),("SENT","Sent"),("FAILED","Failed")])),("delivery_attempts",models.PositiveSmallIntegerField(default=0)),("delivered_at",models.DateTimeField(blank=True,null=True)),("last_delivery_error",models.CharField(max_length=500,blank=True)),("dedupe_key",models.CharField(max_length=255,blank=True,null=True,unique=True)),
            ("recipient",models.ForeignKey(on_delete=models.deletion.PROTECT,related_name="notifications",to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="NotificationPreference", fields=[
            ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),("club_announcements",models.BooleanField(default=True)),("meeting_notifications",models.BooleanField(default=True)),("meeting_reminders",models.BooleanField(default=True)),("user",models.OneToOneField(on_delete=models.deletion.CASCADE,related_name="notification_preferences",to=settings.AUTH_USER_MODEL)),
        ])
    ]
