"""Disposable in-memory Django fixture server used only by browser integration tests."""

import os
import sys
from datetime import timedelta
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(
    DJANGO_SETTINGS_MODULE="config.test_settings",
    DJANGO_TEST_SQLITE="True",
    DJANGO_ENV="test",
    LOGIN_THROTTLE_RATE="100/min",
    SIGNUP_THROTTLE_RATE="100/hour",
)
import django

django.setup()
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.utils import timezone
from events.models import Event

call_command("migrate", verbosity=0, interactive=False)
now = timezone.now()
for title, location, capacity, days in [
    ("Community workshop", "Campus Hall", 1, 2),
    ("Design conversations", "City Library", 10, 4),
    ("Past gathering", "Campus Hall", 5, -2),
]:
    Event.objects.create(
        title=title,
        description="A welcoming space for ideas, learning, and new connections. Join fellow community members for an interactive session.",
        location=location,
        capacity=capacity,
        start_time=now + timedelta(days=days),
        end_time=now + timedelta(days=days, hours=2),
    )


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


with make_server(
    "127.0.0.1", 0, get_wsgi_application(), handler_class=QuietHandler
) as server:
    print(f"TEST_SERVER=http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()
