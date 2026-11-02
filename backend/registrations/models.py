from django.conf import settings
from django.db import models


class Registration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = 'registered', 'Registered'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_registrations')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='registrations')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REGISTERED)
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-registered_at', '-id')
        constraints = [models.UniqueConstraint(fields=('user', 'event'), name='unique_user_event_registration')]

    def __str__(self):
        return f'{self.user} — {self.event} ({self.status})'
