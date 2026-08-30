from __future__ import annotations

from collections.abc import Mapping

from django.core.management.base import BaseCommand, CommandError

from apps.telegram_integration.client import TelegramBotClient
from apps.telegram_integration.exceptions import TelegramAPIError


class Command(BaseCommand):
    help = "Display safe Telegram webhook status without outputting credentials or URLs."

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        try:
            info = TelegramBotClient().get_webhook_info()
        except TelegramAPIError as exc:
            raise CommandError("Telegram webhook status could not be retrieved.") from exc
        if not isinstance(info, Mapping):
            raise CommandError("Telegram webhook status could not be read safely.")
        pending = info.get("pending_update_count", 0)
        pending_count = pending if type(pending) is int and pending >= 0 else 0
        configured = bool(info.get("url"))
        self.stdout.write(f"configured: {'yes' if configured else 'no'}")
        self.stdout.write(f"pending_updates: {pending_count}")
        self.stdout.write(
            f"recent_delivery_error: {'yes' if info.get('last_error_date') else 'no'}"
        )
