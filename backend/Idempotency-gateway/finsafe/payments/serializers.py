from rest_framework import serializers

class PaymentRequestSerializer(serializers.Serializer):
    """Validate payment request body"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    currency = serializers.CharField(max_length=3, required=True)
    
    def validate_currency(self, value):
        # Validate currency code (add more as needed)
        valid_currencies = ['GHS', 'USD', 'EUR', 'GBP', 'NGN', 'KES']
        if value.upper() not in valid_currencies:
            raise serializers.ValidationError(f"Currency must be one of {valid_currencies}")
        return value.upper()

class PaymentResponseSerializer(serializers.Serializer):
    """Payment response format"""
    status = serializers.CharField()
    transaction_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    processed_at = serializers.DateTimeField()
    
class ErrorResponseSerializer(serializers.Serializer):
    """Error response format"""
    error = serializers.CharField()