from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone
from config.api import Conflict
from events.models import Event
from .models import Registration
from .services import register, cancel


@skipUnless(
    connection.vendor == "postgresql",
    "Requires isolated PostgreSQL; SQLite cannot verify row locks.",
)
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.a = get_user_model().objects.create(username="a")
        self.b = get_user_model().objects.create(username="b")
        self.event = Event.objects.create(
            title="Last seat",
            description="Test",
            location="Test",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            capacity=1,
        )

    def race(self, *operations):
        barrier = Barrier(len(operations))

        def execute(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    operation()
                    return "ok"
                except (Conflict, ValidationError):
                    return "conflict"
            finally:
                from django.db import connections

                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(execute, operations))

    def test_two_api_requests_compete_for_last_seat(self):
        outcomes = self.race(
            lambda: register(self.a, self.event.pk),
            lambda: register(self.b, self.event.pk),
        )
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        self.assertEqual(Registration.objects.filter(status="registered").count(), 1)

    def test_api_and_ordinary_admin_model_write_compete(self):
        outcomes = self.race(
            lambda: register(self.a, self.event.pk),
            lambda: Registration.objects.create(user=self.b, event=self.event),
        )
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        self.assertEqual(Registration.objects.filter(status="registered").count(), 1)

    def test_capacity_reduction_and_new_attendee(self):
        self.event.capacity = 2
        self.event.save()
        register(self.a, self.event.pk)

        def reduce():
            event = Event.objects.get(pk=self.event.pk)
            event.capacity = 1
            event.save()

        outcomes = self.race(reduce, lambda: register(self.b, self.event.pk))
        self.assertIn("ok", outcomes)
        self.event.refresh_from_db()
        self.assertLessEqual(
            Registration.objects.filter(status="registered").count(),
            self.event.capacity,
        )

    def test_same_user_concurrent_requests_keep_one_row(self):
        outcomes = self.race(
            lambda: register(self.a, self.event.pk),
            lambda: register(self.a, self.event.pk),
        )
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        self.assertEqual(Registration.objects.count(), 1)

    def test_cancel_and_reactivation_do_not_deadlock_or_overbook(self):
        row, _ = register(self.a, self.event.pk)
        self.race(
            lambda: cancel(self.a, row.pk), lambda: register(self.b, self.event.pk)
        )
        self.assertLessEqual(
            Registration.objects.filter(status="registered").count(), 1
        )

    def test_api_and_admin_http_compete_for_last_seat(self):
        from django.test import Client

        administrator = get_user_model().objects.create_superuser(
            username="staff", password="TestOnly!Password83", email="staff@example.com"
        )

        def admin_add():
            client = Client()
            client.force_login(administrator)
            response = client.post(
                "/admin/registrations/registration/add/",
                {
                    "user": self.b.pk,
                    "event": self.event.pk,
                    "status": "registered",
                    "_save": "Save",
                },
            )
            if response.status_code == 200:
                self.assertIn("The event is full.", response.content.decode())
                raise ValidationError("The event is full.")
            self.assertEqual(response.status_code, 302)

        outcomes = self.race(lambda: register(self.a, self.event.pk), admin_add)
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        self.assertEqual(Registration.objects.filter(status="registered").count(), 1)
