from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.identity.exceptions import (
    AccountUnavailable,
    TelegramInitDataExpired,
    TelegramInitDataInvalid,
    TelegramInitDataReplayed,
)
from apps.identity.models import User


MAX_INIT_DATA_LENGTH = 8_192
MAX_INIT_DATA_FIELDS = 32
MAX_TELEGRAM_METADATA_LENGTH = 128
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_user_id: int
    username: str
    first_name: str
    last_name: str


def _safe_metadata_value(user_data: dict[str, object], field_name: str) -> str:
    value = user_data.get(field_name, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TelegramInitDataInvalid
    return value.strip()[:MAX_TELEGRAM_METADATA_LENGTH]


def _parse_init_data(init_data: str) -> dict[str, str]:
    if not isinstance(init_data, str) or not init_data or len(init_data) > MAX_INIT_DATA_LENGTH:
        raise TelegramInitDataInvalid

    try:
        pairs = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=MAX_INIT_DATA_FIELDS,
            encoding="utf-8",
            errors="strict",
        )
    except (UnicodeDecodeError, ValueError):
        raise TelegramInitDataInvalid from None

    field_names = [field_name for field_name, _ in pairs]
    if len(field_names) != len(set(field_names)):
        raise TelegramInitDataInvalid

    values = dict(pairs)
    received_hash = values.get("hash")
    auth_date = values.get("auth_date")
    user_json = values.get("user")
    if (
        not received_hash
        or len(received_hash) != 64
        or any(character not in "0123456789abcdefABCDEF" for character in received_hash)
        or not auth_date
        or not user_json
    ):
        raise TelegramInitDataInvalid

    data_check_string = "\n".join(
        f"{field_name}={value}"
        for field_name, value in sorted(pairs)
        if field_name != "hash"
    )
    secret_key = hmac.new(
        b"WebAppData",
        settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramInitDataInvalid

    return values


def _validate_auth_date(values: dict[str, str], *, now: int | None = None) -> int:
    raw_auth_date = values["auth_date"]
    try:
        auth_date = int(raw_auth_date)
    except ValueError:
        raise TelegramInitDataInvalid from None

    if auth_date <= 0:
        raise TelegramInitDataInvalid

    current_time = int(time.time()) if now is None else now
    if (
        auth_date > current_time + settings.TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS
        or current_time - auth_date > settings.TELEGRAM_INIT_DATA_MAX_AGE_SECONDS
    ):
        raise TelegramInitDataExpired
    return auth_date


def _consume_replay_hash(received_hash: str, *, auth_date: int, now: int | None = None) -> None:
    current_time = int(time.time()) if now is None else now
    elapsed = max(0, current_time - auth_date)
    timeout = max(1, settings.TELEGRAM_INIT_DATA_MAX_AGE_SECONDS - elapsed)
    digest = hashlib.sha256(received_hash.encode("ascii", "ignore")).hexdigest()
    replay_key = f"identity.telegram_init_data.{digest}"

    try:
        added = cache.add(replay_key, True, timeout=timeout)
    except Exception as exc:  # Cache outages must fail closed without logging payloads.
        logger.error(
            "Telegram replay cache unavailable",
            extra={"exception_type": type(exc).__name__},
        )
        raise TelegramInitDataInvalid from None
    if not added:
        raise TelegramInitDataReplayed


def validate_telegram_init_data(init_data: str, *, now: int | None = None) -> TelegramIdentity:
    """Validate, freshness-check, and consume one Telegram Mini App payload."""

    values = _parse_init_data(init_data)
    auth_date = _validate_auth_date(values, now=now)
    _consume_replay_hash(values["hash"], auth_date=auth_date, now=now)

    try:
        user_data = json.loads(values["user"])
    except (TypeError, json.JSONDecodeError):
        raise TelegramInitDataInvalid from None

    if not isinstance(user_data, dict):
        raise TelegramInitDataInvalid

    telegram_user_id = user_data.get("id")
    if (
        type(telegram_user_id) is not int
        or telegram_user_id <= 0
        or telegram_user_id > 9_223_372_036_854_775_807
    ):
        raise TelegramInitDataInvalid

    return TelegramIdentity(
        telegram_user_id=telegram_user_id,
        username=_safe_metadata_value(user_data, "username"),
        first_name=_safe_metadata_value(user_data, "first_name"),
        last_name=_safe_metadata_value(user_data, "last_name"),
    )


def authenticate_telegram_user(init_data: str) -> User:
    """Resolve the signed Telegram identity to an active application account."""

    identity = validate_telegram_init_data(init_data)
    metadata = {
        "telegram_username": identity.username,
        "telegram_first_name": identity.first_name,
        "telegram_last_name": identity.last_name,
        "last_seen_at": timezone.now(),
    }

    with transaction.atomic():
        user, created = User.objects.select_for_update().get_or_create(
            telegram_user_id=identity.telegram_user_id,
            defaults=metadata,
        )
        if not user.is_active:
            raise AccountUnavailable

        if not created:
            for field_name, value in metadata.items():
                setattr(user, field_name, value)
            user.save(update_fields=(*metadata, "updated_at"))

    return user
