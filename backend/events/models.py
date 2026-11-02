from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('start_time', 'id')
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name='event_capacity_positive'),
            models.CheckConstraint(condition=Q(end_time__gt=models.F('start_time')), name='event_end_after_start'),
        ]

    def clean(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be later than start time.'})
        if self.capacity is not None and self.capacity <= 0:
            raise ValidationError({'capacity': 'Capacity must be greater than zero.'})

    @property
    def available_capacity(self):
        return max(self.capacity - self.registrations.filter(status='registered').count(), 0)

    def __str__(self):
        return self.title
