from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from .models import Registration
from events.models import Event


class AdminCapacityTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_superuser(
            username="admin_test",
            password="NotARealSecret!31",
            email="admin@example.com",
        )
        self.first = U.objects.create(username="first")
        self.second = U.objects.create(username="second")
        self.event = Event.objects.create(
            title="Workshop",
            description="Learn",
            location="Campus",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            capacity=1,
        )
        self.client.force_login(self.admin)

    def test_admin_add_cannot_overbook(self):
        Registration.objects.create(user=self.first, event=self.event)
        response = self.client.post(
            "/admin/registrations/registration/add/",
            {
                "user": self.second.pk,
                "event": self.event.pk,
                "status": "registered",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The event is full.")
        self.assertEqual(Registration.objects.count(), 1)

    def test_admin_reactivate_cannot_overbook(self):
        Registration.objects.create(user=self.first, event=self.event)
        cancelled = Registration.objects.create(
            user=self.second, event=self.event, status="cancelled"
        )
        response = self.client.post(
            f"/admin/registrations/registration/{cancelled.pk}/change/",
            {"status": "registered", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The event is full.")
        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, "cancelled")

    def test_admin_capacity_cannot_drop_below_attendance(self):
        self.event.capacity = 2
        self.event.save()
        Registration.objects.create(user=self.first, event=self.event)
        Registration.objects.create(user=self.second, event=self.event)
        response = self.client.post(
            f"/admin/events/event/{self.event.pk}/change/",
            {
                "title": self.event.title,
                "description": self.event.description,
                "location": self.event.location,
                "start_time_0": self.event.start_time.strftime("%Y-%m-%d"),
                "start_time_1": self.event.start_time.strftime("%H:%M:%S"),
                "end_time_0": self.event.end_time.strftime("%Y-%m-%d"),
                "end_time_1": self.event.end_time.strftime("%H:%M:%S"),
                "capacity": 1,
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "active registrations")
        self.event.refresh_from_db()
        self.assertEqual(self.event.capacity, 2)

    def test_admin_started_event_cannot_add_or_reactivate(self):
        cancelled = Registration.objects.create(
            user=self.second, event=self.event, status="cancelled"
        )
        self.event.start_time = timezone.now() - timedelta(hours=2)
        self.event.end_time = timezone.now() - timedelta(hours=1)
        self.event.save()
        for path, data in [
            (
                "/admin/registrations/registration/add/",
                {"user": self.first.pk, "event": self.event.pk, "status": "registered"},
            ),
            (
                f"/admin/registrations/registration/{cancelled.pk}/change/",
                {"status": "registered"},
            ),
        ]:
            response = self.client.post(path, data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "event has started")

    def test_admin_can_cancel_after_start(self):
        row = Registration.objects.create(user=self.first, event=self.event)
        self.event.start_time = timezone.now() - timedelta(hours=2)
        self.event.end_time = timezone.now() - timedelta(hours=1)
        self.event.save()
        response = self.client.post(
            f"/admin/registrations/registration/{row.pk}/change/",
            {"status": "cancelled", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")

    def test_ordinary_model_saves_enforce_capacity(self):
        Registration.objects.create(user=self.first, event=self.event)
        with self.assertRaises(ValidationError):
            Registration.objects.create(user=self.second, event=self.event)
        self.assertEqual(Registration.objects.count(), 1)

    def test_registration_identity_is_immutable(self):
        row = Registration.objects.create(user=self.first, event=self.event)
        row.user = self.second
        with self.assertRaises(ValidationError):
            row.save()
        row.refresh_from_db()
        self.assertEqual(row.user, self.first)

    def test_no_staff_privileges_no_admin_access(self):
        self.client.force_login(self.first)
        self.assertEqual(self.client.get("/admin/events/event/add/").status_code, 302)
