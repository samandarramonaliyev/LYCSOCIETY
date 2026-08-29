from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from uuid import uuid4


TEST_BOT_TOKEN = "test-bot-token"


def build_signed_init_data(
    *,
    telegram_user_id: int,
    username: str = "student",
    first_name: str = "Telegram",
    last_name: str = "Student",
    auth_date: int | None = None,
    bot_token: str = TEST_BOT_TOKEN,
    query_id: str | None = None,
) -> str:
    values = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": query_id or f"test-query-{uuid4()}",
        "user": json.dumps(
            {
                "id": telegram_user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)
