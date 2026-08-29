from __future__ import annotations

from django.conf import settings
from django.test.runner import DiscoverRunner


class BackendDiscoverRunner(DiscoverRunner):
    """Discover application tests when manage.py is run from the repository root."""

    def build_suite(self, test_labels=None, **kwargs):  # type: ignore[no-untyped-def]
        if not test_labels:
            test_labels = [str(settings.BASE_DIR)]
        return super().build_suite(test_labels, **kwargs)
