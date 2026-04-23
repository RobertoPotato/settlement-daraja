import pytest
import responses

from daraja.models import DarajaRequestLog, DarajaTransaction
from daraja.services import get_daraja_manager


@pytest.mark.django_db
@responses.activate
def test_pay_to_phone_logs_request_and_transaction(daraja_config_override):
    responses.add(
        responses.GET,
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        json={"access_token": "access-token", "expires_in": "3599"},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest",
        json={
            "ConversationID": "conv-001",
            "OriginatorConversationID": "orig-001",
            "ResponseCode": "0",
            "ResponseDescription": "Accept the service request successfully.",
        },
        status=200,
    )

    manager = get_daraja_manager()
    response = manager.pay_to_phone("0712345678", 10, remarks="Unit test payout")

    assert response["ConversationID"] == "conv-001"
    transaction = DarajaTransaction.objects.get(originator_conversation_id="orig-001")
    assert transaction.transaction_type == DarajaTransaction.TYPE_B2C
    assert transaction.status == DarajaTransaction.STATUS_SUBMITTED
    assert transaction.request_payload["PartyB"] == "254712345678"

    request_log = DarajaRequestLog.objects.get(transaction=transaction)
    assert request_log.endpoint == "/mpesa/b2c/v3/paymentrequest"
    assert request_log.success is True


@pytest.mark.django_db
@responses.activate
def test_pay_to_paybill_logs_request_and_transaction(daraja_config_override):
    responses.add(
        responses.GET,
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        json={"access_token": "access-token", "expires_in": "3599"},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://sandbox.safaricom.co.ke/mpesa/b2b/v1/paymentrequest",
        json={
            "ConversationID": "conv-002",
            "OriginatorConversationID": "orig-002",
            "ResponseCode": "0",
            "ResponseDescription": "Accept the service request successfully.",
        },
        status=200,
    )

    manager = get_daraja_manager()
    response = manager.pay_to_paybill("600222", 100, account_reference="ACC123")

    assert response["ConversationID"] == "conv-002"
    transaction = DarajaTransaction.objects.get(originator_conversation_id="orig-002")
    assert transaction.transaction_type == DarajaTransaction.TYPE_B2B
    assert transaction.request_payload["PartyB"] == 600222


@pytest.mark.django_db
@responses.activate
def test_check_balance_creates_transaction(daraja_config_override):
    responses.add(
        responses.GET,
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        json={"access_token": "access-token", "expires_in": "3599"},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://sandbox.safaricom.co.ke/mpesa/accountbalance/v1/query",
        json={
            "ConversationID": "conv-003",
            "OriginatorConversationID": "orig-003",
            "ResponseCode": "0",
            "ResponseDescription": "Accept the service request successfully.",
        },
        status=200,
    )

    manager = get_daraja_manager()
    response = manager.check_balance()

    assert response["ConversationID"] == "conv-003"
    transaction = DarajaTransaction.objects.get(originator_conversation_id="orig-003")
    assert transaction.transaction_type == DarajaTransaction.TYPE_BALANCE


@pytest.mark.django_db
@responses.activate
def test_pay_to_phone_auto_generates_unique_originator_conversation_id(daraja_config_override):
    responses.add(
        responses.GET,
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        json={"access_token": "access-token", "expires_in": "3599"},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest",
        json={
            "ConversationID": "conv-004",
            "OriginatorConversationID": "orig-004",
            "ResponseCode": "0",
            "ResponseDescription": "Accept the service request successfully.",
        },
        status=200,
    )

    manager = get_daraja_manager()
    manager.pay_to_phone("0712345678", 10, remarks="Auto ID test")

    transaction = DarajaTransaction.objects.get(originator_conversation_id="orig-004")
    generated_id = transaction.request_payload.get("OriginatorConversationID")
    assert generated_id
    assert generated_id.startswith("b2c-")
    assert len(generated_id) <= 128


@pytest.mark.django_db
@responses.activate
def test_pay_to_phone_rejects_duplicate_manual_originator_conversation_id(daraja_config_override):
    DarajaTransaction.objects.create(
        transaction_type=DarajaTransaction.TYPE_B2C,
        command_id="BusinessPayment",
        originator_conversation_id="manual-originator-001",
    )

    manager = get_daraja_manager()

    with pytest.raises(ValueError, match="already exists"):
        manager.pay_to_phone(
            phone_number="0712345678",
            amount=10,
            originator_conversation_id="manual-originator-001",
        )
