from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


@override_settings(TELEGRAM_WEBHOOK_ENABLED=True, TELEGRAM_WEBHOOK_SECRET="test-webhook-secret")
class TelegramWebhookManagementCommandTests(SimpleTestCase):
    @patch("apps.telegram_integration.management.commands.configure_telegram_webhook.TelegramBotClient")
    def test_configure_uses_secret_header_and_exact_update_types(self, client_class) -> None:  # type: ignore[no-untyped-def]
        output = StringIO()
        call_command(
            "configure_telegram_webhook",
            "--base-url",
            "https://app.example.com",
            stdout=output,
        )
        client_class.return_value.set_webhook.assert_called_once_with(
            url="https://app.example.com/api/v1/telegram/webhook/",
            secret_token="test-webhook-secret",
            allowed_updates=("message", "chat_join_request"),
        )
        self.assertNotIn("test-webhook-secret", output.getvalue())

    @patch("apps.telegram_integration.management.commands.configure_telegram_webhook.TelegramBotClient")
    def test_delete_does_not_require_or_print_a_webhook_url(self, client_class) -> None:  # type: ignore[no-untyped-def]
        output = StringIO()
        call_command("configure_telegram_webhook", "--delete", stdout=output)
        client_class.return_value.delete_webhook.assert_called_once_with()
        self.assertNotIn("test-webhook-secret", output.getvalue())

    @patch("apps.telegram_integration.management.commands.telegram_webhook_status.TelegramBotClient")
    def test_status_hides_url_and_provider_error_message(self, client_class) -> None:  # type: ignore[no-untyped-def]
        client_class.return_value.get_webhook_info.return_value = {
            "url": "https://app.example.com/api/v1/telegram/webhook/",
            "pending_update_count": 2,
            "last_error_date": 123,
            "last_error_message": "secret-looking detail must stay hidden",
        }
        output = StringIO()
        call_command("telegram_webhook_status", stdout=output)
        value = output.getvalue()
        self.assertIn("configured: yes", value)
        self.assertIn("pending_updates: 2", value)
        self.assertIn("recent_delivery_error: yes", value)
        self.assertNotIn("https://", value)
        self.assertNotIn("secret-looking", value)
