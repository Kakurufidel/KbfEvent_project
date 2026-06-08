from django.contrib import admin
from .models import InvitedGuest, GuestResponse


@admin.register(InvitedGuest)
class InvitedGuestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'event', 'created_at']
    list_filter = ['event']
    search_fields = ['name', 'email']


@admin.register(GuestResponse)
class GuestResponseAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'event', 'will_attend', 'verification_status', 'submitted_at']
    list_filter = ['event', 'will_attend', 'verification_status']
    search_fields = ['name', 'email']
    readonly_fields = ['submitted_at', 'ip_address']
    
    actions = ['mark_as_verified']
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(verification_status='verified')
        self.message_user(request, f'{updated} réponses vérifiées.')
    mark_as_verified.short_description = 'Marquer comme vérifié'