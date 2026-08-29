from __future__ import annotations

import os
from collections.abc import Sequence

from django.core.exceptions import ImproperlyConfigured


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"The {name} environment variable must be set.")
    if value is None:
        raise ImproperlyConfigured(f"The {name} environment variable has no default value.")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ImproperlyConfigured(f"The {name} environment variable must be a boolean value.")


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"The {name} environment variable must be an integer.") from exc


def env_list(name: str, default: Sequence[str] = ()) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]
