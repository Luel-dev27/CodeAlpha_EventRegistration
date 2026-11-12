from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from config.api import Conflict
from events.models import Event
from .models import Registration


def register(user, event_id):
    try:
        with transaction.atomic():
            event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
            registration = (
                Registration.objects.select_for_update()
                .filter(user=user, event=event)
                .first()
            )
            if registration and registration.status == Registration.Status.REGISTERED:
                raise Conflict("You are already registered for this event.")
            created = registration is None
            if created:
                registration = Registration(user=user, event=event)
            else:
                registration.status = Registration.Status.REGISTERED
                registration.registered_at = timezone.now()
            registration.save()
            return registration, created
    except ValidationError as exc:
        raise Conflict(" ".join(exc.messages)) from exc
    except IntegrityError as exc:
        name = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if (
            name == "unique_user_event_registration"
            or "UNIQUE constraint failed: registrations_registration.user_id, registrations_registration.event_id"
            in str(exc)
        ):
            raise Conflict("You are already registered for this event.") from exc
        raise


def cancel(user, registration_id):
    # Owner-filter before acquiring locks; do not disclose other users' records.
    row = get_object_or_404(Registration.objects.filter(user=user), pk=registration_id)
    with transaction.atomic():
        get_object_or_404(Event.objects.select_for_update(), pk=row.event_id)
        registration = get_object_or_404(
            Registration.objects.select_for_update().filter(user=user),
            pk=registration_id,
        )
        already_cancelled = registration.status == Registration.Status.CANCELLED
        if not already_cancelled:
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=("status", "updated_at"))
        return registration, already_cancelled
