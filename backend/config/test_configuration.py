import os
import subprocess
import sys
from django.test import SimpleTestCase
from django.conf import settings


class ConfigurationTests(SimpleTestCase):
    def check_config(self, values):
        env = {
            **os.environ,
            "DJANGO_ENV": "production",
            "DJANGO_DEBUG": "False",
            "DJANGO_ALLOWED_HOSTS": "events.example.org",
            "DJANGO_TEST_SQLITE": "False",
            "SECURE_SSL_REDIRECT": "True",
            **values,
        }
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "manage.py",
                "check",
                "--deploy",
                "--settings=config.settings",
            ],
            cwd=settings.BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_production_checks(self):
        result = self.check_config({})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no issues", result.stdout + result.stderr)

    def test_unsafe_production_configuration_fails_closed(self):
        for settings_override in [
            {"DJANGO_SECRET_KEY": ""},
            {"DJANGO_SECRET_KEY": "unsafe-development-key-change-me"},
            {"DJANGO_DEBUG": "True"},
            {"DJANGO_ALLOWED_HOSTS": "*"},
            {"DJANGO_ALLOWED_HOSTS": "https://wrong.example"},
            {"DJANGO_TEST_SQLITE": "True"},
            {"SECURE_SSL_REDIRECT": "False"},
            {"CORS_ALLOWED_ORIGINS": "*"},
            {"DJANGO_DEBUG": "not-a-bool"},
        ]:
            with self.subTest(setting=next(iter(settings_override))):
                self.assertNotEqual(self.check_config(settings_override).returncode, 0)
