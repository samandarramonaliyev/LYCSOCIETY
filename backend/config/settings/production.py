from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if DEBUG:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_DEBUG must be false when using production settings.")
