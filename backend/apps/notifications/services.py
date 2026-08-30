from django.utils import timezone
from .models import Notification, DeliveryStatus

def create_notification(*, recipient, type, title, body, dedupe_key=None):
    obj, _ = Notification.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={"recipient": recipient, "type": type, "title": title, "body": body},
    ) if dedupe_key else (Notification.objects.create(recipient=recipient, type=type, title=title, body=body), True)
    return obj

def deliver_notification(notification, client):
    from apps.telegram_integration.exceptions import TelegramIntegrationError
    notification.delivery_attempts += 1
    try:
        client.send_message(notification.recipient.telegram_user_id, f"{notification.title}\n\n{notification.body}")
    except Exception as exc:
        notification.delivery_status = DeliveryStatus.FAILED
        # Persist only a safe error category. Provider text can contain request URLs,
        # invite links, or credentials and must not become durable application data.
        notification.last_delivery_error = type(exc).__name__[:500]
        notification.save(update_fields=("delivery_attempts", "delivery_status", "last_delivery_error", "updated_at"))
        return False
    notification.delivery_status = DeliveryStatus.SENT
    notification.delivered_at = timezone.now()
    notification.last_delivery_error = ""
    notification.save(update_fields=("delivery_attempts", "delivery_status", "delivered_at", "last_delivery_error", "updated_at"))
    return True
