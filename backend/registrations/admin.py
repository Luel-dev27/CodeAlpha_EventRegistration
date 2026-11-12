from django.contrib import admin
from django.db import transaction

from events.models import Event
from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "event", "status", "registered_at", "updated_at")
    list_filter = ("status", "registered_at")
    search_fields = ("user__username", "user__email", "event__title")
    readonly_fields = ("registered_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (("user", "event") if obj else ())

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        with transaction.atomic():
            if request.method == "POST":
                if object_id and str(object_id).isdigit():
                    event_id = (
                        Registration.objects.filter(pk=object_id)
                        .values_list("event_id", flat=True)
                        .first()
                    )
                else:
                    value = request.POST.get("event", "")
                    event_id = int(value) if value.isdigit() else None
                if event_id:
                    Event.objects.select_for_update().filter(pk=event_id).first()
            return super().changeform_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        with transaction.atomic():
            if request.method == "POST" and str(object_id).isdigit():
                event_id = (
                    Registration.objects.filter(pk=object_id)
                    .values_list("event_id", flat=True)
                    .first()
                )
                if event_id:
                    Event.objects.select_for_update().filter(pk=event_id).first()
            return super().delete_view(request, object_id, extra_context)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            list(
                Event.objects.select_for_update()
                .filter(pk__in=queryset.values("event_id"))
                .order_by("pk")
            )
            return super().delete_queryset(request, queryset)
