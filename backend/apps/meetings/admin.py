from django.contrib import admin
from .models import Meeting, MeetingRSVP, Announcement
admin.site.register(Meeting); admin.site.register(MeetingRSVP); admin.site.register(Announcement)
