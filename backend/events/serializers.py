from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    available_capacity = serializers.IntegerField(read_only=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'location', 'start_time', 'end_time', 'capacity',
                  'available_capacity', 'created_at', 'updated_at')
        read_only_fields = ('id', 'available_capacity', 'created_at', 'updated_at')

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        errors = {}
        if start and end and end <= start:
            errors['end_time'] = 'End time must be later than start time.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Capacity must be greater than zero.')
        return value

    def validate_end_time(self, value):
        start = self.initial_data.get('start_time')
        if start:
            start = serializers.DateTimeField().to_internal_value(start)
        else:
            start = getattr(self.instance, 'start_time', None)
        if start and value <= start:
            raise serializers.ValidationError('End time must be later than start time.')
        return value
