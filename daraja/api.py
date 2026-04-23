"""
Secured API endpoints for triggering Daraja M-Pesa operations.
Requires Django authentication. All endpoints are class-based views using Django REST Framework.
"""

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from daraja.models import DarajaTransaction
from daraja.serializers import (
    CheckBalanceSerializer,
    PayToPaybillSerializer,
    PayToPhoneSerializer,
)
from daraja.services import get_daraja_manager


class DarajaPermission(IsAuthenticated):
    """
    Custom permission to ensure user has access to Daraja operations.
    Currently requires only authentication; can be extended for role-based access control.
    """

    message = "You do not have permission to access Daraja API endpoints."


@method_decorator(login_required, name="dispatch")
class PayToPhoneAPIView(APIView):
    """
    API endpoint to trigger B2C (pay to phone) payout.

    POST /api/daraja/pay-to-phone/
    {
        "phone_number": "0712345678",
        "amount": "100.50",
        "remarks": "Salary payment",
        "occasion": "Monthly salary",
        "command_id": "BusinessPayment"
    }

    Returns:
    {
        "originator_conversation_id": "abc-123-def",
        "conversation_id": "def-456-ghi",
        "status": "submitted",
        "response_code": "0",
        "response_description": "Accept the service request successfully.",
        "message": "B2C payout initiated successfully. Track with originator_conversation_id."
    }
    """

    permission_classes = [DarajaPermission]

    def post(self, request):
        """Process B2C payout request with input validation."""
        serializer = PayToPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            manager = get_daraja_manager()
            response = manager.pay_to_phone(
                phone_number=serializer.validated_data["phone_number"],
                amount=int(serializer.validated_data["amount"]),
                remarks=serializer.validated_data.get("remarks", ""),
                occasion=serializer.validated_data.get("occasion", ""),
                command_id=serializer.validated_data.get("command_id", "BusinessPayment"),
            )

            # Retrieve transaction for response
            originator_conversation_id = response.get("OriginatorConversationID", "")
            transaction = DarajaTransaction.objects.get(
                originator_conversation_id=originator_conversation_id
            )

            response_data = {
                "originator_conversation_id": transaction.originator_conversation_id,
                "conversation_id": transaction.conversation_id,
                "status": transaction.status,
                "response_code": response.get("ResponseCode", ""),
                "response_description": response.get("ResponseDescription", ""),
                "message": "B2C payout initiated successfully. Track with originator_conversation_id.",
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {
                    "error": "validation_error",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "api_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(login_required, name="dispatch")
class PayToPaybillAPIView(APIView):
    """
    API endpoint to trigger B2B (pay to paybill) payout.

    POST /api/daraja/pay-to-paybill/
    {
        "receiver_shortcode": "600222",
        "amount": "1000.00",
        "account_reference": "INV-2024-001",
        "remarks": "Payment for invoice",
        "receiver_identifier_type": "4",
        "command_id": "BusinessToBusinessTransfer"
    }

    Returns:
    {
        "originator_conversation_id": "abc-123-def",
        "conversation_id": "def-456-ghi",
        "status": "submitted",
        "response_code": "0",
        "response_description": "Accept the service request successfully.",
        "message": "B2B payout initiated successfully. Track with originator_conversation_id."
    }
    """

    permission_classes = [DarajaPermission]

    def post(self, request):
        """Process B2B payout request with input validation."""
        serializer = PayToPaybillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            manager = get_daraja_manager()
            response = manager.pay_to_paybill(
                receiver_shortcode=serializer.validated_data["receiver_shortcode"],
                amount=int(serializer.validated_data["amount"]),
                account_reference=serializer.validated_data.get("account_reference", ""),
                remarks=serializer.validated_data.get("remarks", ""),
                receiver_identifier_type=serializer.validated_data.get("receiver_identifier_type", "4"),
                command_id=serializer.validated_data.get(
                    "command_id", "BusinessToBusinessTransfer"
                ),
            )

            # Retrieve transaction for response
            originator_conversation_id = response.get("OriginatorConversationID", "")
            transaction = DarajaTransaction.objects.get(
                originator_conversation_id=originator_conversation_id
            )

            response_data = {
                "originator_conversation_id": transaction.originator_conversation_id,
                "conversation_id": transaction.conversation_id,
                "status": transaction.status,
                "response_code": response.get("ResponseCode", ""),
                "response_description": response.get("ResponseDescription", ""),
                "message": "B2B payout initiated successfully. Track with originator_conversation_id.",
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {
                    "error": "validation_error",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "api_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(login_required, name="dispatch")
class CheckBalanceAPIView(APIView):
    """
    API endpoint to query account balance asynchronously.

    POST /api/daraja/check-balance/
    {
        "identifier_type": "4"
    }

    Returns:
    {
        "originator_conversation_id": "abc-123-def",
        "conversation_id": "def-456-ghi",
        "status": "submitted",
        "response_code": "0",
        "response_description": "Accept the service request successfully.",
        "message": "Balance query initiated. Result will be delivered to callback URL."
    }

    Note: Balance result is delivered asynchronously via callback webhook.
    """

    permission_classes = [DarajaPermission]

    def post(self, request):
        """Process balance check request."""
        serializer = CheckBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            manager = get_daraja_manager()
            response = manager.check_balance(
                identifier_type=serializer.validated_data.get("identifier_type", "4"),
            )

            # Retrieve transaction for response
            originator_conversation_id = response.get("OriginatorConversationID", "")
            transaction = DarajaTransaction.objects.get(
                originator_conversation_id=originator_conversation_id
            )

            response_data = {
                "originator_conversation_id": transaction.originator_conversation_id,
                "conversation_id": transaction.conversation_id,
                "status": transaction.status,
                "response_code": response.get("ResponseCode", ""),
                "response_description": response.get("ResponseDescription", ""),
                "message": "Balance query initiated. Result will be delivered to callback URL.",
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {
                    "error": "validation_error",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "api_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(login_required, name="dispatch")
class TransactionStatusAPIView(APIView):
    """
    API endpoint to retrieve transaction status by conversation ID.

    GET /api/daraja/transaction-status/?originator_conversation_id=abc-123-def

    Returns:
    {
        "id": 1,
        "transaction_type": "b2c",
        "command_id": "BusinessPayment",
        "status": "success",
        "amount": "100.50",
        "party_a": "600980",
        "party_b": "254712345678",
        "conversation_id": "def-456-ghi",
        "originator_conversation_id": "abc-123-def",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:31:45Z"
    }
    """

    permission_classes = [DarajaPermission]

    def get(self, request):
        """Retrieve transaction status by conversation ID."""
        originator_conversation_id = request.query_params.get(
            "originator_conversation_id"
        )
        conversation_id = request.query_params.get("conversation_id")

        if not originator_conversation_id and not conversation_id:
            return Response(
                {
                    "error": "validation_error",
                    "message": "Either 'originator_conversation_id' or 'conversation_id' query parameter is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if originator_conversation_id:
                transaction = DarajaTransaction.objects.get(
                    originator_conversation_id=originator_conversation_id
                )
            else:
                transaction = DarajaTransaction.objects.get(
                    conversation_id=conversation_id
                )

            transaction_data = {
                "id": transaction.id,
                "transaction_type": transaction.transaction_type,
                "command_id": transaction.command_id,
                "status": transaction.status,
                "amount": str(transaction.amount),
                "party_a": transaction.party_a,
                "party_b": transaction.party_b,
                "account_reference": transaction.account_reference,
                "conversation_id": transaction.conversation_id,
                "originator_conversation_id": transaction.originator_conversation_id,
                "created_at": transaction.created_at.isoformat(),
                "updated_at": transaction.updated_at.isoformat(),
            }

            return Response(transaction_data, status=status.HTTP_200_OK)

        except DarajaTransaction.DoesNotExist:
            return Response(
                {
                    "error": "not_found",
                    "message": "Transaction not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "error": "server_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
