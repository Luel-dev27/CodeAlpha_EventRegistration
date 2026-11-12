from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Registration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="registrations"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.REGISTERED
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-registered_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "event"), name="unique_user_event_registration"
            )
        ]

    def _validate_rules(self, event, previous):
        if self.status not in self.Status.values:
            raise ValidationError({"status": "Choose a valid registration status."})
        if previous and (
            previous.event_id != self.event_id or previous.user_id != self.user_id
        ):
            raise ValidationError(
                "An existing registration cannot be moved to another user or event."
            )
        if self.status == self.Status.REGISTERED:
            activating = previous is None or previous.status != self.Status.REGISTERED
            if activating and event.start_time <= timezone.now():
                raise ValidationError(
                    "Registration is closed because the event has started."
                )
            count = (
                type(self)
                .objects.filter(event_id=self.event_id, status=self.Status.REGISTERED)
                .exclude(pk=self.pk)
                .count()
            )
            if count >= event.capacity:
                raise ValidationError("The event is full.")

    def clean(self):
        super().clean()
        if self.event_id and self.user_id:
            previous = (
                type(self).objects.filter(pk=self.pk).first() if self.pk else None
            )
            self._validate_rules(self.event, previous)

    def save(self, *args, **kwargs):
        from events.models import Event

        # All supported writes acquire the event first, then the registration.
        with transaction.atomic():
            try:
                event = Event.objects.select_for_update().get(pk=self.event_id)
            except Event.DoesNotExist as exc:
                raise ValidationError("The event no longer exists.") from exc
            previous = (
                type(self).objects.select_for_update().filter(pk=self.pk).first()
                if self.pk
                else None
            )
            self._validate_rules(event, previous)
            self.event = event
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} — {self.event} ({self.status})"
