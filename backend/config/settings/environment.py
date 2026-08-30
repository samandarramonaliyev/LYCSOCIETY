from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
import re

from django.core.exceptions import ImproperlyConfigured


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}
ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def load_development_environment(path: Path) -> None:
    """Load a local dotenv-style file without overriding the process environment.

    This is deliberately called only by ``config.settings.development``. Production
    configuration comes exclusively from the deployment environment or secret
    manager, so an arbitrary checked-out ``.env`` file can never affect it.
    """

    if not path.is_file():
        return

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ImproperlyConfigured(
            "The local .env file could not be read. Copy .env.example to .env and check its permissions."
        ) from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ImproperlyConfigured(
                f"Invalid local .env syntax on line {line_number}. Use NAME=value without exposing secrets in errors."
            )

        name, value = line.split("=", maxsplit=1)
        name = name.strip()
        value = value.strip()
        if not ENVIRONMENT_NAME.fullmatch(name):
            raise ImproperlyConfigured(
                f"Invalid local .env variable name on line {line_number}."
            )
        if value.startswith(("'", '"')):
            quote = value[0]
            if len(value) < 2 or not value.endswith(quote):
                raise ImproperlyConfigured(
                    f"Unterminated quoted local .env value on line {line_number}."
                )
            value = value[1:-1]

        # A deployment shell or IDE launch configuration always takes precedence.
        os.environ.setdefault(name, value)


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"The {name} environment variable must be set. For local development, copy "
            ".env.example to .env and configure it; production must provide it through "
            "the deployment environment or secret manager."
        )
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
