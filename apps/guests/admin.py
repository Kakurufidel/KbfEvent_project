# apps/guests/admin.py
from django.contrib import admin
from .models import InvitedGuest, GuestResponse

@admin.register(InvitedGuest)
class InvitedGuestAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_name', 'email', 'event', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('event',)
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'

@admin.register(GuestResponse)
class GuestResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_name', 'email', 'event', 'will_attend', 'verification_status', 'submitted_at')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('event', 'will_attend', 'verification_status')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'