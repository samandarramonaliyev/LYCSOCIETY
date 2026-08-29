from django.db import migrations, models
import uuid
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    initial=True
    dependencies=[("clubs","0001_initial")]
    operations=[
        migrations.CreateModel(name="ClubTelegramGroup", fields=[("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),("telegram_chat_id",models.BigIntegerField(unique=True)),("telegram_chat_title",models.CharField(max_length=255,blank=True)),("status",models.CharField(max_length=12,default="LINKED",choices=[("PENDING","Pending"),("LINKED","Linked"),("UNLINKED","Unlinked")])),("bot_can_invite_members",models.BooleanField(default=False)),("bot_can_send_messages",models.BooleanField(default=False)),("linked_at",models.DateTimeField(blank=True,null=True)),("unlinked_at",models.DateTimeField(blank=True,null=True)),("club",models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name="telegram_group",to="clubs.club"))]),
        migrations.CreateModel(name="TelegramLinkChallenge", fields=[("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),("token_hash",models.CharField(max_length=64,unique=True)),("expires_at",models.DateTimeField()),("used_at",models.DateTimeField(blank=True,null=True)),("club",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="telegram_link_challenges",to="clubs.club"))]),
    ]
