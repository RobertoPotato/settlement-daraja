"""
Serializers for Daraja API request/response validation using Django REST Framework.
Provides input validation and response formatting for B2C, B2B, and balance operations.
"""

from decimal import Decimal

from rest_framework import serializers


class PayToPhoneSerializer(serializers.Serializer):
    """Serializer for B2C (pay to phone) requests."""

    phone_number = serializers.CharField(
        max_length=20,
        help_text="Phone number in format 07XX..., +254XX..., or 254XX...",
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1"),
        help_text="Amount in KES (minimum 1 KES)",
    )
    remarks = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Transaction remarks/description",
    )
    occasion = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Transaction occasion/reason",
    )
    command_id = serializers.CharField(
        max_length=100,
        required=False,
        default="BusinessPayment",
        help_text="Daraja command ID (SalaryPayment, BusinessPayment, PromotionPayment)",
    )


class PayToPaybillSerializer(serializers.Serializer):
    """Serializer for B2B (pay to paybill/bank) requests."""

    receiver_shortcode = serializers.CharField(
        max_length=50,
        help_text="Paybill or bank code (6 digits)",
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1"),
        help_text="Amount in KES (minimum 1 KES)",
    )
    account_reference = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Account reference/invoice number at receiver",
    )
    remarks = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Transaction remarks/description",
    )
    receiver_identifier_type = serializers.CharField(
        max_length=50,
        required=False,
        default="4",
        help_text="Identifier type (4=shortcode, 1=msisdn). Defaults to 4.",
    )
    command_id = serializers.CharField(
        max_length=100,
        required=False,
        default="BusinessToBusinessTransfer",
        help_text="Daraja command ID (BusinessPayBill, BusinessToBusinessTransfer)",
    )


class CheckBalanceSerializer(serializers.Serializer):
    """Serializer for balance check requests."""

    identifier_type = serializers.CharField(
        max_length=50,
        required=False,
        default="4",
        help_text="Identifier type (4=shortcode, 1=msisdn). Defaults to 4.",
    )


class TransactionResponseSerializer(serializers.Serializer):
    """Serializer for transaction response."""

    originator_conversation_id = serializers.CharField(
        help_text="Unique identifier for tracking transaction"
    )
    conversation_id = serializers.CharField(
        help_text="Daraja conversation ID"
    )
    status = serializers.CharField(
        help_text="Transaction status (submitted, success, failed, timeout)"
    )
    response_code = serializers.CharField(
        required=False,
        help_text="Daraja response code from API",
    )
    response_description = serializers.CharField(
        required=False,
        help_text="Daraja response description from API",
    )
    message = serializers.CharField(
        help_text="Human-readable message"
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    error = serializers.CharField(help_text="Error code/type")
    message = serializers.CharField(help_text="Error message")
    details = serializers.DictField(
        required=False,
        help_text="Additional error context",
    )
