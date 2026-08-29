from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.clubs.models import Club
class MeetingStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    CANCELLED = "CANCELLED", "Cancelled"
class Meeting(UUIDTimeStampedModel):
    club=models.ForeignKey(Club,on_delete=models.CASCADE,related_name="meetings")
    title=models.CharField(max_length=200)
    description=models.TextField(max_length=3000,blank=True)
    starts_at=models.DateTimeField()
    location=models.CharField(max_length=300,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_meetings")
    status=models.CharField(max_length=12,choices=MeetingStatus.choices,default=MeetingStatus.SCHEDULED)
class MeetingRSVP(UUIDTimeStampedModel):
    class Response(models.TextChoices):
        GOING="GOING","Going"; NOT_GOING="NOT_GOING","Not going"
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name="rsvps")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="meeting_rsvps")
    response=models.CharField(max_length=12,choices=Response.choices)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("meeting","user"),name="meetings_rsvp_unique")]
class Announcement(UUIDTimeStampedModel):
    club=models.ForeignKey(Club,on_delete=models.CASCADE,related_name="announcements")
    title=models.CharField(max_length=200)
    message=models.TextField(max_length=5000)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_announcements")
