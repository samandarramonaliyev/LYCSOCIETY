from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from .exceptions import TelegramAPIError


class TelegramBotClient:
    def _call(self, method, payload):  # type: ignore[no-untyped-def]
        request = Request(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=8) as response:
                data = json.loads(response.read())
        except HTTPError as exc:
            raise TelegramAPIError(
                "Telegram API unavailable",
                retryable=exc.code == 429 or exc.code >= 500,
            ) from exc
        except (URLError, OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TelegramAPIError("Telegram API unavailable") from exc
        if not isinstance(data, Mapping) or not data.get("ok"):
            error_code = data.get("error_code") if isinstance(data, Mapping) else None
            raise TelegramAPIError(
                "Telegram API request failed",
                retryable=not isinstance(error_code, int) or error_code == 429 or error_code >= 500,
            )
        return data["result"]

    def send_message(self, chat_id, text):  # type: ignore[no-untyped-def]
        return self._call("sendMessage", {"chat_id": chat_id, "text": text})

    def create_invite_link(
        self,
        chat_id,
        *,
        expire_date=None,
        creates_join_request=True,
    ):  # type: ignore[no-untyped-def]
        payload = {
            "chat_id": chat_id,
            "creates_join_request": bool(creates_join_request),
        }
        if expire_date:
            payload["expire_date"] = expire_date
        return self._call("createChatInviteLink", payload)

    def revoke_invite_link(self, chat_id, invite_link):  # type: ignore[no-untyped-def]
        return self._call(
            "revokeChatInviteLink",
            {"chat_id": chat_id, "invite_link": invite_link},
        )

    def get_me(self):  # type: ignore[no-untyped-def]
        return self._call("getMe", {})

    def get_chat(self, chat_id):  # type: ignore[no-untyped-def]
        return self._call("getChat", {"chat_id": chat_id})

    def get_chat_member(self, chat_id, user_id):  # type: ignore[no-untyped-def]
        return self._call("getChatMember", {"chat_id": chat_id, "user_id": user_id})

    def approve_chat_join_request(self, chat_id, user_id):  # type: ignore[no-untyped-def]
        return self._call("approveChatJoinRequest", {"chat_id": chat_id, "user_id": user_id})

    def decline_chat_join_request(self, chat_id, user_id):  # type: ignore[no-untyped-def]
        return self._call("declineChatJoinRequest", {"chat_id": chat_id, "user_id": user_id})

    def set_webhook(self, *, url, secret_token, allowed_updates):  # type: ignore[no-untyped-def]
        return self._call(
            "setWebhook",
            {
                "url": url,
                "secret_token": secret_token,
                "allowed_updates": list(allowed_updates),
            },
        )

    def delete_webhook(self):  # type: ignore[no-untyped-def]
        return self._call("deleteWebhook", {})

    def get_webhook_info(self):  # type: ignore[no-untyped-def]
        return self._call("getWebhookInfo", {})
