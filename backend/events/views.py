from django.db.models import F, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny

from config.api import OptionalPagination
from .models import Event
from .serializers import EventSerializer


def event_queryset(request):
    from registrations.models import Registration

    queryset = Event.objects.with_capacity()
    if request.user.is_authenticated:
        mine = Registration.objects.filter(user=request.user, event_id=OuterRef("pk"))
        queryset = queryset.annotate(
            registration_status=Subquery(mine.values("status")[:1])
        )
    return queryset


class EventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = (AllowAny,)
    pagination_class = OptionalPagination

    def get_queryset(self):
        queryset = event_queryset(self.request)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(location__icontains=search)
            )
        when = self.request.query_params.get("when")
        if when:
            if when not in {"upcoming", "past"}:
                raise ValidationError({"when": "Use upcoming or past."})
            queryset = (
                queryset.filter(start_time__gt=timezone.now())
                if when == "upcoming"
                else queryset.filter(start_time__lte=timezone.now())
            )
        available = self.request.query_params.get("available")
        if available is not None:
            if available not in {"true", "false"}:
                raise ValidationError({"available": "Use true or false."})
            condition = Q(active_registration_count__lt=F("capacity"))
            queryset = queryset.filter(condition if available == "true" else ~condition)
        return queryset.order_by("start_time", "id")


class EventDetailView(generics.RetrieveAPIView):
    serializer_class = EventSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        return event_queryset(self.request)
