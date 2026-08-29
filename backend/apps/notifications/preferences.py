from rest_framework import serializers
from .models import NotificationPreference
class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model=NotificationPreference; fields=("club_announcements","meeting_notifications","meeting_reminders")
