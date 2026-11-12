from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Q


class EventQuerySet(models.QuerySet):
    def with_capacity(self):
        return self.annotate(
            active_registration_count=Count(
                "registrations", filter=Q(registrations__status="registered")
            )
        )


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ("start_time", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(capacity__gt=0), name="event_capacity_positive"
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F("start_time")),
                name="event_end_after_start",
            ),
        ]

    def clean(self):
        errors = {}
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            errors["end_time"] = "End time must be later than start time."
        if self.capacity is not None and self.capacity <= 0:
            errors["capacity"] = "Capacity must be greater than zero."
        elif self.pk and self.capacity is not None:
            count = self.registrations.filter(status="registered").count()
            if self.capacity < count:
                errors["capacity"] = (
                    f"Capacity cannot be less than the {count} active registrations."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                type(self).objects.select_for_update().get(pk=self.pk)
            self.clean()
            return super().save(*args, **kwargs)

    @property
    def available_capacity(self):
        count = getattr(self, "active_registration_count", None)
        if count is None:
            count = self.registrations.filter(status="registered").count()
        return max(self.capacity - count, 0)

    def __str__(self):
        return self.title
