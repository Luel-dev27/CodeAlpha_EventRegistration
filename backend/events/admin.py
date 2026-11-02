from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'start_time', 'end_time', 'capacity', 'created_at')
    list_filter = ('start_time', 'location')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('created_at', 'updated_at')
