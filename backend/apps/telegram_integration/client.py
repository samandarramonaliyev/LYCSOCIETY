from __future__ import annotations

import json
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
        except Exception as exc:
            raise TelegramAPIError("Telegram API unavailable") from exc
        if not data.get("ok"):
            raise TelegramAPIError("Telegram API request failed")
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
