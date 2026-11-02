from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event
from .models import Registration

User = get_user_model()


class AuthenticationAndRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = Event.objects.create(
            title='API Conference', description='Talks and workshops', location='Addis Ababa',
            start_time=timezone.now() + timedelta(days=4),
            end_time=timezone.now() + timedelta(days=4, hours=5), capacity=1,
        )
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='StrongPass123!')
        self.other = User.objects.create_user(username='bob', email='bob@example.com', password='StrongPass123!')

    def authenticate(self, user=None):
        user = user or self.user
        from rest_framework.authtoken.models import Token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=user)[0].key}')

    def test_user_registration(self):
        response = self.client.post(reverse('auth-register'), {
            'username': 'charlie', 'email': 'charlie@example.com', 'password': 'StrongPass123!'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['token'])
        self.assertNotIn('password', response.data['user'])

    def test_login_and_logout(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'alice', 'password': 'StrongPass123!'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        logout = self.client.post(reverse('auth-logout'), format='json')
        self.assertEqual(logout.status_code, 200)

    def test_successful_registration(self):
        self.authenticate()
        response = self.client.post(reverse('registrations:registration-list-create'), {'event_id': self.event.id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], Registration.Status.REGISTERED)

    def test_duplicate_registration_prevented(self):
        self.authenticate()
        url = reverse('registrations:registration-list-create')
        self.assertEqual(self.client.post(url, {'event_id': self.event.id}, format='json').status_code, 201)
        self.assertEqual(self.client.post(url, {'event_id': self.event.id}, format='json').status_code, 409)
        self.assertEqual(Registration.objects.filter(user=self.user, event=self.event).count(), 1)

    def test_full_event_rejected(self):
        Registration.objects.create(user=self.other, event=self.event)
        self.authenticate()
        response = self.client.post(reverse('registrations:registration-list-create'), {'event_id': self.event.id}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_past_event_rejected(self):
        past = Event.objects.create(
            title='Past', description='Past event', location='Here',
            start_time=timezone.now() - timedelta(days=2), end_time=timezone.now() - timedelta(days=1), capacity=2,
        )
        self.authenticate()
        response = self.client.post(reverse('registrations:registration-list-create'), {'event_id': past.id}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_list_and_detail_are_private(self):
        registration = Registration.objects.create(user=self.user, event=self.event)
        self.authenticate(self.other)
        self.assertEqual(self.client.get(reverse('registrations:registration-list-create')).data, [])
        self.assertEqual(self.client.get(reverse('registrations:registration-detail', args=(registration.id,))).status_code, 404)

    def test_cancellation_ownership_and_reregistration(self):
        self.authenticate()
        url = reverse('registrations:registration-list-create')
        response = self.client.post(url, {'event_id': self.event.id}, format='json')
        registration_id = response.data['id']
        self.authenticate(self.other)
        self.assertEqual(self.client.post(reverse('registrations:registration-cancel', args=(registration_id,))).status_code, 404)
        self.authenticate()
        self.assertEqual(self.client.post(reverse('registrations:registration-cancel', args=(registration_id,))).status_code, 200)
        self.assertEqual(self.client.post(url, {'event_id': self.event.id}, format='json').status_code, 200)
        self.assertEqual(Registration.objects.filter(user=self.user, event=self.event).count(), 1)
        self.assertEqual(Registration.objects.get(user=self.user, event=self.event).status, Registration.Status.REGISTERED)

    def test_cancelled_registration_does_not_count_capacity(self):
        Registration.objects.create(user=self.other, event=self.event, status=Registration.Status.CANCELLED)
        self.authenticate()
        response = self.client.post(reverse('registrations:registration-list-create'), {'event_id': self.event.id}, format='json')
        self.assertEqual(response.status_code, 201)
