from django.contrib import admin
from .models import IdempotencyRecord, InFlightLock


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ('idempotency_key', 'status_code', 'created_at', 'expires_at')
    search_fields = ('idempotency_key',)


@admin.register(InFlightLock)
class InFlightLockAdmin(admin.ModelAdmin):
    list_display = ('idempotency_key', 'locked_at', 'expires_at')
    search_fields = ('idempotency_key',)
