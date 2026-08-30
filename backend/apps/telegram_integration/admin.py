from django.contrib import admin
from .models import ClubTelegramGroup, TelegramLinkChallenge, TelegramWebhookUpdate
admin.site.register(ClubTelegramGroup)
admin.site.register(TelegramLinkChallenge)
admin.site.register(TelegramWebhookUpdate)
