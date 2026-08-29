from django.core.management.base import BaseCommand
from apps.notifications.models import Notification, DeliveryStatus
from apps.notifications.services import deliver_notification
from apps.telegram_integration.client import TelegramBotClient

class Command(BaseCommand):
    help = "Deliver pending Telegram notifications (maximum three attempts)."
    def add_arguments(self, parser): parser.add_argument("--limit", type=int, default=100)
    def handle(self, *args, **options):
        qs = Notification.objects.filter(delivery_status__in=[DeliveryStatus.PENDING, DeliveryStatus.FAILED], delivery_attempts__lt=3).order_by("created_at")[:options["limit"]]
        sent = sum(deliver_notification(n, TelegramBotClient()) for n in qs)
        self.stdout.write(self.style.SUCCESS(f"Delivered: {sent}"))
