from rest_framework.exceptions import APIException

class TelegramIntegrationError(Exception):
    pass


class TelegramAPIError(TelegramIntegrationError):
    def __init__(self, message: str = "Telegram API unavailable", *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class LinkChallengeError(APIException):
    status_code = 400
    default_code = "TELEGRAM_LINK_INVALID"
    default_detail = "Telegram group linking could not be completed."
