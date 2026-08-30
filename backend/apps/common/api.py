from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class StandardPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _message_from_detail(detail: Any) -> str:
    if isinstance(detail, Mapping):
        if "detail" in detail:
            return str(detail["detail"])
        return "Request validation failed."
    if isinstance(detail, list):
        return str(detail[0]) if detail else "Request validation failed."
    return str(detail)


def _fields_from_detail(detail: Any) -> dict[str, Any]:
    if not isinstance(detail, Mapping):
        return {}
    return {key: value for key, value in detail.items() if key != "detail"}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Return a stable, non-leaking error envelope for DRF responses."""

    response = drf_exception_handler(exc, context)
    if response is None:
        # Do not interpolate exception text or traceback into the default log. Database
        # and provider exceptions can contain roster input, URLs, or credentials.
        logger.error(
            "Unhandled API exception",
            extra={"exception_type": type(exc).__name__},
        )
        return Response(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "fields": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    default_code = getattr(exc, "default_code", "REQUEST_ERROR")
    response.data = {
        "error": {
            "code": str(default_code).upper(),
            "message": _message_from_detail(detail),
            "fields": _fields_from_detail(detail),
        }
    }
    return response
