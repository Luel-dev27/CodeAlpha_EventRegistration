from django.contrib import admin

from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'event', 'status', 'registered_at', 'updated_at')
    list_filter = ('status', 'registered_at')
    search_fields = ('user__username', 'user__email', 'event__title')
    readonly_fields = ('registered_at', 'updated_at')
