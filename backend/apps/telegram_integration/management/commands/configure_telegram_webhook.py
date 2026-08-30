from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.telegram_integration.client import TelegramBotClient
from apps.telegram_integration.exceptions import TelegramAPIError
from apps.telegram_integration.webhook import TELEGRAM_ALLOWED_UPDATES


WEBHOOK_PATH = "/api/v1/telegram/webhook/"


def build_webhook_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.path.rstrip("/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise CommandError("--base-url must be an exact public HTTPS origin.")
    try:
        if parsed.port not in {None, 80, 88, 443, 8443}:
            raise CommandError("--base-url uses an unsupported Telegram webhook port.")
    except ValueError as exc:
        raise CommandError("--base-url must contain a valid HTTPS port.") from exc
    try:
        if not ipaddress.ip_address(hostname).is_global:
            raise CommandError("--base-url must use a public HTTPS hostname.")
    except ValueError:
        if hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise CommandError("--base-url must use a public HTTPS hostname.")
    return f"{base_url.rstrip('/')}{WEBHOOK_PATH}"


class Command(BaseCommand):
    help = "Configure or delete the secret-protected LYC Society Telegram webhook."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--base-url", help="Exact public HTTPS application origin.")
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete the configured Telegram webhook without printing credentials.",
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        delete = options["delete"]
        base_url = options.get("base_url")
        if delete and base_url:
            raise CommandError("--delete cannot be combined with --base-url.")
        client = TelegramBotClient()
        try:
            if delete:
                client.delete_webhook()
                self.stdout.write(self.style.SUCCESS("Telegram webhook deleted."))
                return
            if not settings.TELEGRAM_WEBHOOK_ENABLED:
                raise CommandError("TELEGRAM_WEBHOOK_ENABLED must be true before configuration.")
            if not base_url:
                raise CommandError("--base-url is required when configuring a webhook.")
            client.set_webhook(
                url=build_webhook_url(base_url),
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                allowed_updates=TELEGRAM_ALLOWED_UPDATES,
            )
        except TelegramAPIError as exc:
            raise CommandError("Telegram webhook configuration failed.") from exc
        self.stdout.write(
            self.style.SUCCESS(
                "Telegram webhook configured for the LYC Society endpoint with restricted update types."
            )
        )
