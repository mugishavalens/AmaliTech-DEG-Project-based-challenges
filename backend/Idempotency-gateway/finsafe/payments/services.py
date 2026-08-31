# payments/services.py

import hashlib
import json
import time
import uuid
from datetime import timedelta
from django.db import IntegrityError
from django.utils import timezone
from .models import IdempotencyRecord, InFlightLock

class IdempotencyService:
    """
    Core service handling idempotency logic with race condition protection
    """
    
    @staticmethod
    def generate_request_hash(request_body):
        """Generate a hash of the request body for comparison"""
        # Sort keys to ensure consistent hash
        sorted_body = json.dumps(request_body, sort_keys=True, default=str)
        return hashlib.sha256(sorted_body.encode()).hexdigest()
    
    @staticmethod
    def simulate_payment_processing(amount, currency):
        """
        Simulate payment processing with 2-second delay
        In production, this would call an actual payment gateway
        """
        import time
        time.sleep(2)  # Simulate processing time
        
        # Generate fake transaction ID
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        
        return {
            "status": f"Charged {amount} {currency}",
            "transaction_id": transaction_id,
            "amount": str(amount),
            "currency": currency,
            "processed_at": timezone.now().isoformat()
        }
    
    @staticmethod
    def acquire_lock(idempotency_key, timeout_seconds=5):
        """
        Acquire a lock for this key to prevent race conditions.
        The database's unique constraint on idempotency_key is the single
        source of truth, so only one concurrent request can ever win it,
        even across separate worker processes.
        Returns True if lock acquired, False if already locked.
        """
        # Clean up expired locks first so stale locks don't block new requests
        InFlightLock.objects.filter(expires_at__lt=timezone.now()).delete()

        try:
            InFlightLock.objects.create(
                idempotency_key=idempotency_key,
                expires_at=timezone.now() + timedelta(seconds=timeout_seconds)
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    def release_lock(idempotency_key):
        """Release the lock for this key"""
        InFlightLock.objects.filter(idempotency_key=idempotency_key).delete()
    
    @staticmethod
    def get_or_create_record(idempotency_key, request_body, process_callback):
        """
        Main idempotency logic with race condition protection
        """
        request_hash = IdempotencyService.generate_request_hash(request_body)
        
        # 1: Check if already processed
        try:
            existing_record = IdempotencyRecord.objects.get(
                idempotency_key=idempotency_key
            )
            if existing_record.expires_at and existing_record.expires_at < timezone.now():
    
                existing_record.delete()  
                return {
                'error': 'Idempotency key expired',
                'status_code': 410
             }
            # Verify request body matches
            existing_hash = IdempotencyService.generate_request_hash(
                existing_record.request_body
            )
            
            if existing_hash != request_hash:
                return {
                    'error': 'Idempotency key already used for a different request body.',
                    'status_code': 422
                }
            
            # Return cached response
            return {
                'response': existing_record.response_body,
                'status_code': existing_record.status_code,
                'cached': True
            }
            
        except IdempotencyRecord.DoesNotExist:
            #  2: Acquire lock to prevent race condition
            lock_acquired = IdempotencyService.acquire_lock(idempotency_key)
            
            if not lock_acquired:
                # Another request is processing - wait and then fetch result
                max_wait = 5  # Maximum wait time in seconds
                wait_interval = 0.1  # Check every 100ms
                waited = 0
                
                while waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    
                    try:
                        # Check if record now exists
                        record = IdempotencyRecord.objects.get(
                            idempotency_key=idempotency_key
                        )
                        return {
                            'response': record.response_body,
                            'status_code': record.status_code,
                            'cached': True
                        }
                    except IdempotencyRecord.DoesNotExist:
                        continue
                
                
                return {
                    'error': 'Request processing timeout. Please try again.',
                    'status_code': 504
                }
            
            try:
                # 3: Process the payment
                response_data = process_callback(request_body)
                
                # 4: Store the result
                record = IdempotencyRecord.objects.create(
                    idempotency_key=idempotency_key,
                    request_body_hash=request_hash,
                    # request_body=request_body,
                    # response_body=response_data,
                    request_body=json.loads(json.dumps(request_body, default=str)),
                    response_body=json.loads(json.dumps(response_data, default=str)),
                    status_code=200,
                    expires_at=timezone.now() + timedelta(minutes=10)  
                )
                
                return {
                    'response': response_data,
                    'status_code': 200,
                    'cached': False
                }
                
            finally:
               
                IdempotencyService.release_lock(idempotency_key)