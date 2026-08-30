from rest_framework import serializers
from .models import NotificationPreference
class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model=NotificationPreference; fields=("club_announcements","meeting_notifications","meeting_reminders")

    def validate(self, attrs):
        submitted = set(self.initial_data) if isinstance(self.initial_data, dict) else set()
        unexpected = sorted(submitted - set(self.fields))
        if unexpected:
            raise serializers.ValidationError(
                {field: "This field is not writable." for field in unexpected}
            )
        return attrs
