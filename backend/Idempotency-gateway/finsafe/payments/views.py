import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .serializers import PaymentRequestSerializer, PaymentResponseSerializer, ErrorResponseSerializer
from .services import IdempotencyService

@method_decorator(csrf_exempt, name='dispatch')
class ProcessPaymentView(APIView):
    """
    Payment processing endpoint with idempotency support
    """

    @extend_schema(
        summary="Process a payment (idempotent)",
        description=(
            "Processes a payment exactly once per `Idempotency-Key`. Retrying the same key "
            "with the same body returns the original cached response (`X-Cache-Hit: true`) "
            "instead of charging again."
        ),
        parameters=[
            OpenApiParameter(
                name='Idempotency-Key',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Unique client-generated string identifying this transaction attempt.',
            ),
        ],
        request=PaymentRequestSerializer,
        responses={
            200: PaymentResponseSerializer,
            400: ErrorResponseSerializer,
            410: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
            504: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        """
        Handle POST /api/process-payment
        """
        #  1: Extract and validate Idempotency-Key header
        idempotency_key = request.headers.get('Idempotency-Key')
        
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2: Validate request body
        serializer = PaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': f'Invalid request body: {serializer.errors}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3: Extract validated data
        amount = serializer.validated_data['amount']
        currency = serializer.validated_data['currency']
        
        # 4: Define payment processing callback
        def process_payment(request_body):
            """Callback that actually processes the payment"""
            return IdempotencyService.simulate_payment_processing(
                amount=request_body['amount'],
                currency=request_body['currency']
            )
        
        #  5: Execute idempotency logic
        result = IdempotencyService.get_or_create_record(
            idempotency_key=idempotency_key,
            request_body=serializer.validated_data,
            process_callback=process_payment
        )
        
        #  6: Handle errors
        if 'error' in result:
            return Response(
                {'error': result['error']},
                status=result['status_code']
            )
        
        #  7: Return success response with cache header
        response = Response(
            result['response'],
            status=result['status_code']
        )
        
        # Add cache header
        if result.get('cached', False):
            response['X-Cache-Hit'] = 'true'
        else:
            response['X-Cache-Hit'] = 'false'
        
        return response

class HealthCheckView(APIView):
    """
    Health check endpoint
    """

    @extend_schema(summary="Health check", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({
            'status': 'OK',
            'service': 'Idempotency Gateway',
            'timestamp': time.time(),
            'version': '1.0.0'
        })
