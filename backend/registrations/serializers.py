from rest_framework import serializers

from events.models import Event
from events.serializers import EventSerializer
from .models import Registration


class RegistrationSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all(), source='event', write_only=True)

    class Meta:
        model = Registration
        fields = ('id', 'event', 'event_id', 'status', 'registered_at', 'updated_at')
        read_only_fields = ('id', 'status', 'registered_at', 'updated_at')
