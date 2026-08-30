from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings.environment import load_development_environment


class DevelopmentEnvironmentLoaderTests(SimpleTestCase):
    def test_loads_local_values_without_overriding_process_environment(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch.dict(os.environ, {}, clear=True):
            dotenv_path = Path(temporary_directory) / ".env"
            dotenv_path.write_text(
                "# local values\nDJANGO_SECRET_KEY='local secret'\nDJANGO_DB_PORT=55432\n",
                encoding="utf-8",
            )
            os.environ["DJANGO_DB_PORT"] = "65432"

            load_development_environment(dotenv_path)

            self.assertEqual(os.environ["DJANGO_SECRET_KEY"], "local secret")
            self.assertEqual(os.environ["DJANGO_DB_PORT"], "65432")

    def test_rejects_malformed_input_without_echoing_the_value(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch.dict(os.environ, {}, clear=True):
            dotenv_path = Path(temporary_directory) / ".env"
            dotenv_path.write_text("INVALID-NAME=not-a-real-secret\n", encoding="utf-8")

            with self.assertRaisesRegex(ImproperlyConfigured, "line 1") as context:
                load_development_environment(dotenv_path)

        self.assertNotIn("not-a-real-secret", str(context.exception))
