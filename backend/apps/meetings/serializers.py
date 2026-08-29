from rest_framework import serializers
from .models import Meeting, Announcement, MeetingRSVP
class MeetingSerializer(serializers.ModelSerializer):
    class Meta: model=Meeting; fields=("id","title","description","starts_at","location","status","created_at")
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta: model=Announcement; fields=("id","title","message","created_at")
class RSVPSerializer(serializers.ModelSerializer):
    class Meta: model=MeetingRSVP; fields=("response",)
