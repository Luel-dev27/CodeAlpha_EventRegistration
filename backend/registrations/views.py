from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event
from .models import Registration
from .serializers import RegistrationSerializer


class RegistrationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The event is full or registration is no longer available.'
    default_code = 'registration_conflict'


class RegistrationListCreateView(generics.ListCreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user).select_related('event')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.validated_data['event']
        try:
            with transaction.atomic():
                locked_event = Event.objects.select_for_update().get(pk=event.pk)
                if locked_event.end_time <= locked_event.start_time:
                    raise RegistrationConflict('Event has invalid time bounds.')
                if locked_event.start_time <= timezone.now():
                    raise RegistrationConflict('Registration is closed because the event has started.')
                existing = Registration.objects.select_for_update().filter(
                    user=request.user, event=locked_event
                ).first()
                active_count = Registration.objects.filter(
                    event=locked_event, status=Registration.Status.REGISTERED
                ).count()
                if existing and existing.status == Registration.Status.REGISTERED:
                    raise RegistrationConflict('You are already registered for this event.')
                if active_count >= locked_event.capacity:
                    raise RegistrationConflict('The event is full.')
                if existing:
                    existing.status = Registration.Status.REGISTERED
                    existing.registered_at = timezone.now()
                    existing.save(update_fields=('status', 'registered_at', 'updated_at'))
                    registration = existing
                    response_status = status.HTTP_200_OK
                else:
                    registration = Registration.objects.create(user=request.user, event=locked_event)
                    response_status = status.HTTP_201_CREATED
        except IntegrityError as exc:
            raise RegistrationConflict('You are already registered for this event.') from exc
        return Response(self.get_serializer(registration).data, status=response_status)


class RegistrationDetailView(generics.RetrieveAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user).select_related('event')


class RegistrationCancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        with transaction.atomic():
            registration = get_object_or_404(
                Registration.objects.select_for_update().filter(user=request.user).select_related('event'), pk=pk
            )
            if registration.status == Registration.Status.CANCELLED:
                return Response({'detail': 'Registration is already cancelled.'}, status=status.HTTP_200_OK)
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=('status', 'updated_at'))
        return Response(RegistrationSerializer(registration).data, status=status.HTTP_200_OK)
