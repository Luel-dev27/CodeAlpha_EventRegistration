from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event
from .models import Registration

User = get_user_model()


class SecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="attendee", password="Str0ng!DifferentPass"
        )
        self.other = User.objects.create_user(
            username="other", password="Str0ng!DifferentPass"
        )
        self.event = Event.objects.create(
            title="Future workshop",
            description="Learn together",
            location="Campus",
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=2),
            capacity=1,
        )

    def auth(self):
        from rest_framework.authtoken.models import Token

        token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return token.key

    def test_configured_password_validators(self):
        for password in ["short", "password", "12345678", "newstudent"]:
            with self.subTest(password_type="invalid"):
                cache.clear()
                response = self.client.post(
                    "/api/auth/register/",
                    {"username": "newstudent", "password": password},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("password", response.data)
                self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_signup_hashes_password_and_does_not_expose_it(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "newstudent", "password": "Lemon!Garden72.Wind"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            User.objects.get(username="newstudent").check_password(
                "Lemon!Garden72.Wind"
            )
        )
        self.assertNotIn("password", response.data["user"])

    def test_duplicate_username_and_email(self):
        self.user.email = "existing@example.com"
        self.user.save()
        for payload in [
            {"username": "attendee", "password": "Lemon!Garden72.Wind"},
            {
                "username": "new",
                "email": "EXISTING@example.com",
                "password": "Lemon!Garden72.Wind",
            },
        ]:
            self.assertEqual(
                self.client.post(
                    "/api/auth/register/", payload, format="json"
                ).status_code,
                400,
            )

    def test_unauthorized_and_invalid_token(self):
        for path, method in [
            ("/api/registrations/", "get"),
            ("/api/registrations/", "post"),
            ("/api/registrations/1/", "get"),
            ("/api/registrations/1/cancel/", "post"),
        ]:
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid")
        self.assertEqual(self.client.get("/api/registrations/").status_code, 401)

    def test_login_failure_and_logout_revocation(self):
        self.assertEqual(
            self.client.post(
                "/api/auth/login/",
                {"username": "attendee", "password": "wrong"},
                format="json",
            ).status_code,
            400,
        )
        key = self.auth()
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        self.assertEqual(self.client.get("/api/registrations/").status_code, 401)

    def test_invalid_registration_input(self):
        self.auth()
        for payload in [
            {},
            {"event_id": 99999},
            {"event_id": "wrong"},
            {"event_id": None},
        ]:
            self.assertEqual(
                self.client.post(
                    "/api/registrations/", payload, format="json"
                ).status_code,
                400,
            )
        self.assertEqual(Registration.objects.count(), 0)

    def test_cannot_choose_another_user_or_status(self):
        self.auth()
        response = self.client.post(
            "/api/registrations/",
            {"event_id": self.event.pk, "user": self.other.pk, "status": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        row = Registration.objects.get()
        self.assertEqual(row.user, self.user)
        self.assertEqual(row.status, "registered")

    def test_invalid_status_filter(self):
        self.auth()
        self.assertEqual(
            self.client.get("/api/registrations/?status=other").status_code, 400
        )

    def test_reactivation_cannot_take_a_full_seat(self):
        self.auth()
        mine = Registration.objects.create(
            user=self.user, event=self.event, status="cancelled"
        )
        Registration.objects.create(user=self.other, event=self.event)
        response = self.client.post(
            "/api/registrations/", {"event_id": self.event.pk}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        mine.refresh_from_db()
        self.assertEqual(mine.status, "cancelled")

    def test_cancel_is_idempotent_and_owner_only(self):
        mine = Registration.objects.create(user=self.user, event=self.event)
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post(f"/api/registrations/{mine.pk}/cancel/").status_code, 404
        )
        self.client.force_authenticate(self.user)
        for _ in range(2):
            self.assertEqual(
                self.client.post(f"/api/registrations/{mine.pk}/cancel/").status_code,
                200,
            )
        self.assertEqual(self.event.available_capacity, 1)

    def test_concurrent_event_deletion_is_404(self):
        self.auth()
        with patch(
            "registrations.services.get_object_or_404",
            side_effect=Http404("The event no longer exists."),
        ):
            response = self.client.post(
                "/api/registrations/", {"event_id": self.event.pk}, format="json"
            )
        self.assertEqual(response.status_code, 404)

    def test_unrelated_database_failure_is_safe_500_and_rolls_back(self):
        self.auth()
        with patch(
            "registrations.models.Registration.save",
            side_effect=IntegrityError("private database detail"),
        ):
            response = self.client.post(
                "/api/registrations/", {"event_id": self.event.pk}, format="json"
            )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private", str(response.data))
        self.assertEqual(Registration.objects.count(), 0)

    def test_signup_token_failure_rolls_back_account(self):
        with patch(
            "registrations.auth_views.Token.objects.get_or_create",
            side_effect=IntegrityError("private"),
        ):
            response = self.client.post(
                "/api/auth/register/",
                {"username": "rollback", "password": "Lemon!Garden72.Wind"},
                format="json",
            )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(User.objects.filter(username="rollback").exists())

    def test_throttles(self):
        with patch(
            "registrations.throttles.LoginThrottle.rate", "2/min", create=True
        ), patch(
            "registrations.throttles.LoginThrottle.get_rate", return_value="2/min"
        ):
            for _ in range(2):
                self.assertEqual(
                    self.client.post("/api/auth/login/", {}, format="json").status_code,
                    400,
                )
            response = self.client.post("/api/auth/login/", {}, format="json")
            self.assertEqual(response.status_code, 429)
            self.assertIn("Retry-After", response)
        cache.clear()
        with patch(
            "registrations.throttles.SignupThrottle.get_rate", return_value="1/hour"
        ):
            self.assertEqual(
                self.client.post("/api/auth/register/", {}, format="json").status_code,
                400,
            )
            self.assertEqual(
                self.client.post("/api/auth/register/", {}, format="json").status_code,
                429,
            )
        cache.clear()
        self.auth()
        with patch(
            "registrations.throttles.RegistrationThrottle.get_rate",
            return_value="1/min",
        ):
            self.assertEqual(
                self.client.post("/api/registrations/", {}, format="json").status_code,
                400,
            )
            self.assertEqual(
                self.client.post("/api/registrations/", {}, format="json").status_code,
                429,
            )

    def test_private_responses_not_cached(self):
        self.auth()
        self.assertEqual(
            self.client.get("/api/registrations/")["Cache-Control"], "no-store"
        )
