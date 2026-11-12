from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Event
from registrations.models import Registration


class EventFeaturesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()
        self.upcoming = Event.objects.create(
            title="Python workshop",
            description="Learning",
            location="Campus",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
            capacity=2,
        )
        self.past = Event.objects.create(
            title="Past meetup",
            description="History",
            location="Town",
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=1),
            capacity=2,
        )

    def test_search_title_and_location(self):
        for term in ["PYTHON", "campus"]:
            data = self.client.get("/api/events/", {"search": term}).data
            self.assertEqual([row["id"] for row in data], [self.upcoming.pk])

    def test_time_filters(self):
        for value, event in [("upcoming", self.upcoming), ("past", self.past)]:
            data = self.client.get("/api/events/", {"when": value}).data
            self.assertEqual([row["id"] for row in data], [event.pk])

    def test_availability(self):
        U = get_user_model()
        Registration.objects.create(
            user=U.objects.create(username="first"), event=self.upcoming
        )
        Registration.objects.create(
            user=U.objects.create(username="second"), event=self.upcoming
        )
        data = self.client.get("/api/events/", {"available": "false"}).data
        self.assertEqual([row["id"] for row in data], [self.upcoming.pk])
        self.assertEqual(data[0]["available_capacity"], 0)

    def test_invalid_filters_and_missing_event(self):
        self.assertEqual(self.client.get("/api/events/?when=bad").status_code, 400)
        self.assertEqual(
            self.client.get("/api/events/?available=maybe").status_code, 400
        )
        self.assertEqual(self.client.get("/api/events/9999/").status_code, 404)

    def test_optional_pagination_preserves_legacy_arrays(self):
        self.assertIsInstance(self.client.get("/api/events/").data, list)
        response = self.client.get("/api/events/?page=1&page_size=1")
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["next"])
        self.assertEqual(self.client.get("/api/events/?page=999").status_code, 404)

    def test_personal_status_and_no_n_plus_one(self):
        user = get_user_model().objects.create(username="mine")
        Registration.objects.create(user=user, event=self.upcoming)
        self.client.force_authenticate(user)
        with CaptureQueriesContext(connection) as queries:
            result = self.client.get("/api/events/").data
        self.assertLessEqual(len(queries), 2)
        self.assertEqual(
            next(r for r in result if r["id"] == self.upcoming.pk)[
                "registration_status"
            ],
            "registered",
        )
        self.client.force_authenticate(None)
        self.assertTrue(
            all(
                row["registration_status"] is None
                for row in self.client.get("/api/events/").data
            )
        )

    def test_registration_list_capacity_count_is_batched(self):
        user = get_user_model().objects.create(username="mine")
        Registration.objects.create(user=user, event=self.upcoming)
        self.client.force_authenticate(user)
        with CaptureQueriesContext(connection) as queries:
            data = self.client.get("/api/registrations/?page=1&status=registered").data
        self.assertLessEqual(len(queries), 3)
        self.assertEqual(data["results"][0]["event"]["available_capacity"], 1)
