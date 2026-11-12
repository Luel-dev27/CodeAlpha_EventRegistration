from django.contrib import admin
from django.db import transaction

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "location",
        "start_time",
        "end_time",
        "capacity",
        "created_at",
    )
    list_filter = ("start_time", "location")
    search_fields = ("title", "description", "location")
    readonly_fields = ("created_at", "updated_at")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Hold the lock through form validation and save, so errors stay in the form.
        with transaction.atomic():
            if request.method == "POST" and object_id and str(object_id).isdigit():
                Event.objects.select_for_update().filter(pk=object_id).first()
            return super().changeform_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        with transaction.atomic():
            if request.method == "POST" and str(object_id).isdigit():
                Event.objects.select_for_update().filter(pk=object_id).first()
            return super().delete_view(request, object_id, extra_context)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            list(
                Event.objects.select_for_update()
                .filter(pk__in=queryset.values("pk"))
                .order_by("pk")
            )
            return super().delete_queryset(request, queryset)
