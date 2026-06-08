from django.contrib import admin
from .models import Event, EventCollaborator


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'main_organizer', 'event_type', 'date', 'is_active']
    list_filter = ['event_type', 'is_active']
    search_fields = ['name', 'location']
    readonly_fields = ['rsvp_token', 'coorganizer_token', 'slug', 'created_at']


@admin.register(EventCollaborator)
class EventCollaboratorAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'status', 'invited_at']
    list_filter = ['status']
    search_fields = ['event__name', 'user__email']