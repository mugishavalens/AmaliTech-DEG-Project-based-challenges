from django.urls import path
from .views import ProcessPaymentView, HealthCheckView

urlpatterns = [
    path('api/process-payment', ProcessPaymentView.as_view(), name='process-payment'),
    path('api/health', HealthCheckView.as_view(), name='health'),
]