from __future__ import annotations

from rest_framework.exceptions import APIException, AuthenticationFailed, PermissionDenied


class TelegramInitDataInvalid(AuthenticationFailed):
    default_detail = "Telegram authentication data could not be validated."
    default_code = "TELEGRAM_INIT_DATA_INVALID"


class TelegramInitDataExpired(AuthenticationFailed):
    default_detail = "Telegram authentication data has expired."
    default_code = "TELEGRAM_INIT_DATA_EXPIRED"


class TelegramInitDataReplayed(AuthenticationFailed):
    default_detail = "Telegram authentication data could not be validated."
    default_code = "TELEGRAM_INIT_DATA_REPLAYED"


class AccountUnavailable(PermissionDenied):
    default_detail = "This account is not available."
    default_code = "ACCOUNT_UNAVAILABLE"


class VerificationClaimFailed(APIException):
    status_code = 400
    default_detail = "We could not verify those student details. Contact an administrator if you need help."
    default_code = "VERIFICATION_FAILED"


class AlreadyVerified(APIException):
    status_code = 409
    default_detail = "This account is already verified. Contact an administrator to correct an identity claim."
    default_code = "ALREADY_VERIFIED"
