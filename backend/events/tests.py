from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event


class EventAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = Event.objects.create(
            title='Backend Meetup', description='A technical meetup', location='Addis Ababa',
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=2), capacity=2,
        )

    def test_event_list(self):
        response = self.client.get(reverse('events:event-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], self.event.id)

    def test_event_detail(self):
        response = self.client.get(reverse('events:event-detail', args=(self.event.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], self.event.title)

    def test_invalid_event_data_rejected(self):
        payload = {
            'title': 'Bad', 'description': 'Invalid time range', 'location': 'Here',
            'start_time': timezone.now() + timedelta(days=3),
            'end_time': timezone.now() + timedelta(days=2), 'capacity': 0,
        }
        from .serializers import EventSerializer
        serializer = EventSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('end_time', serializer.errors)
        self.assertIn('capacity', serializer.errors)
