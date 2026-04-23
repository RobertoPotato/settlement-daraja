import pytest
from django.urls import reverse

from daraja.models import DarajaCallbackLog, DarajaTransaction


@pytest.mark.django_db
def test_b2c_result_callback_marks_transaction_success(client):
    transaction = DarajaTransaction.objects.create(
        transaction_type=DarajaTransaction.TYPE_B2C,
        command_id="BusinessPayment",
        originator_conversation_id="orig-100",
    )

    payload = {
        "Result": {
            "ResultType": 0,
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "OriginatorConversationID": "orig-100",
            "ConversationID": "conv-100",
        }
    }

    response = client.post(
        reverse("daraja:b2c_result"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200
    transaction.refresh_from_db()
    assert transaction.status == DarajaTransaction.STATUS_SUCCESS
    callback_log = DarajaCallbackLog.objects.get(transaction=transaction)
    assert callback_log.callback_type == DarajaCallbackLog.CALLBACK_B2C_RESULT
    assert callback_log.result_code == 0


@pytest.mark.django_db
def test_b2b_timeout_callback_marks_transaction_timeout(client):
    transaction = DarajaTransaction.objects.create(
        transaction_type=DarajaTransaction.TYPE_B2B,
        command_id="BusinessPayBill",
        originator_conversation_id="orig-200",
    )

    payload = {
        "Result": {
            "ResultType": 1,
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user.",
            "OriginatorConversationID": "orig-200",
            "ConversationID": "conv-200",
        }
    }

    response = client.post(
        reverse("daraja:b2b_timeout"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200
    transaction.refresh_from_db()
    assert transaction.status == DarajaTransaction.STATUS_TIMEOUT
    callback_log = DarajaCallbackLog.objects.get(transaction=transaction)
    assert callback_log.callback_type == DarajaCallbackLog.CALLBACK_B2B_TIMEOUT


@pytest.mark.django_db
def test_balance_result_callback_without_transaction_is_logged(client):
    payload = {
        "Result": {
            "ResultType": 0,
            "ResultCode": 0,
            "ResultDesc": "Balance returned.",
            "OriginatorConversationID": "orig-300",
            "ConversationID": "conv-300",
        }
    }

    response = client.post(
        reverse("daraja:balance_result"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200
    callback_log = DarajaCallbackLog.objects.get(originator_conversation_id="orig-300")
    assert callback_log.transaction is None
    assert callback_log.result_code == 0
