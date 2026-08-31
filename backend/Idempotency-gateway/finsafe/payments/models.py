from django.db import models
from django.utils import timezone
import json



class IdempotencyRecord(models.Model):
    """
    Stores idempotency keys and their responses
    """
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    request_body_hash = models.CharField(max_length=64)  # Store hash of request body
    request_body = models.JSONField()  # Store original request
    response_body = models.JSONField()  # Store response to return
    status_code = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.idempotency_key} - {self.created_at}"
    
    @classmethod
    def cleanup_old_records(cls, days=7):
        """Delete records older than specified days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = cls.objects.filter(created_at__lt=cutoff_date).delete()
        return deleted_count[0] if deleted_count else 0

class InFlightLock(models.Model):
    """
    For race condition handling - prevents concurrent processing
    """
    idempotency_key = models.CharField(max_length=255, unique=True)
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at