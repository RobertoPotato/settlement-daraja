from django.urls import path

from . import api, views

app_name = "daraja"

# Callback webhook endpoints (public, CSRF-exempt)
callback_patterns = [
    path("daraja/b2c/callback/result/", views.B2CResultCallbackView.as_view(), name="b2c_result"),
    path("daraja/b2c/callback/timeout/", views.B2CTimeoutCallbackView.as_view(), name="b2c_timeout"),
    path("daraja/b2b/callback/result/", views.B2BResultCallbackView.as_view(), name="b2b_result"),
    path("daraja/b2b/callback/timeout/", views.B2BTimeoutCallbackView.as_view(), name="b2b_timeout"),
    path("daraja/balance/callback/result/", views.BalanceResultCallbackView.as_view(), name="balance_result"),
    path("daraja/balance/callback/timeout/", views.BalanceTimeoutCallbackView.as_view(), name="balance_timeout"),
]

# Internal API endpoints (secured, require authentication)
api_patterns = [
    path("pay-to-phone/", api.PayToPhoneAPIView.as_view(), name="pay_to_phone"),
    path("pay-to-paybill/", api.PayToPaybillAPIView.as_view(), name="pay_to_paybill"),
    path("check-balance/", api.CheckBalanceAPIView.as_view(), name="check_balance"),
    path("transaction-status/", api.TransactionStatusAPIView.as_view(), name="transaction_status"),
]

urlpatterns = callback_patterns + api_patterns
