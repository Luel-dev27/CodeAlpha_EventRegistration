from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import OptionalPagination
from .models import Registration
from .serializers import RegistrationSerializer
from .services import cancel, register
from .throttles import RegistrationThrottle


class RegistrationListCreateView(generics.ListCreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = OptionalPagination

    def get_throttles(self):
        return [RegistrationThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        queryset = (
            Registration.objects.filter(user=self.request.user)
            .select_related("event")
            .annotate(
                active_count=Count(
                    "event__registrations",
                    filter=Q(event__registrations__status="registered"),
                )
            )
        )
        selected = self.request.query_params.get("status")
        if selected:
            if selected not in Registration.Status.values:
                raise ValidationError({"status": "Use registered or cancelled."})
            queryset = queryset.filter(status=selected)
        return queryset.order_by("-registered_at", "-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration, created = register(
            request.user, serializer.validated_data["event"].pk
        )
        return Response(
            self.get_serializer(registration).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RegistrationDetailView(generics.RetrieveAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return RegistrationListCreateView.get_queryset(self)


class RegistrationCancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        registration, already_cancelled = cancel(request.user, pk)
        if already_cancelled:
            return Response({"detail": "Registration is already cancelled."})
        return Response(RegistrationSerializer(registration).data)
