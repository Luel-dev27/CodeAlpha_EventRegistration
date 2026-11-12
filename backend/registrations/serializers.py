from rest_framework import serializers

from events.models import Event
from events.serializers import EventSerializer
from .models import Registration


class RegistrationSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(), source="event", write_only=True
    )

    class Meta:
        model = Registration
        fields = ("id", "event", "event_id", "status", "registered_at", "updated_at")
        read_only_fields = ("id", "status", "registered_at", "updated_at")

    def get_event(self, obj):
        if hasattr(obj, "active_count"):
            obj.event.active_registration_count = obj.active_count
        return EventSerializer(obj.event, context=self.context).data
