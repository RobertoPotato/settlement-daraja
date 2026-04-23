import pytest

from daraja.forms import B2CWithdrawalForm
from daraja.models import DarajaTransaction


@pytest.mark.django_db
def test_b2c_form_requires_originator_conversation_id_in_manual_mode():
    form = B2CWithdrawalForm(
        data={
            "environment": "sandbox",
            "phone_number": "0712345678",
            "amount": "10",
            "remarks": "",
            "occasion": "",
            "command_id": "BusinessPayment",
            "originator_id_mode": "manual",
            "originator_conversation_id": "",
        }
    )

    assert not form.is_valid()
    assert "originator_conversation_id" in form.errors


@pytest.mark.django_db
def test_b2c_form_rejects_duplicate_manual_originator_conversation_id():
    DarajaTransaction.objects.create(
        transaction_type=DarajaTransaction.TYPE_B2C,
        command_id="BusinessPayment",
        originator_conversation_id="manual-dup-001",
    )

    form = B2CWithdrawalForm(
        data={
            "environment": "sandbox",
            "phone_number": "0712345678",
            "amount": "10",
            "remarks": "",
            "occasion": "",
            "command_id": "BusinessPayment",
            "originator_id_mode": "manual",
            "originator_conversation_id": "manual-dup-001",
        }
    )

    assert not form.is_valid()
    assert "originator_conversation_id" in form.errors


@pytest.mark.django_db
def test_b2c_form_auto_mode_ignores_manual_originator_conversation_id():
    form = B2CWithdrawalForm(
        data={
            "environment": "sandbox",
            "phone_number": "0712345678",
            "amount": "10",
            "remarks": "",
            "occasion": "",
            "command_id": "BusinessPayment",
            "originator_id_mode": "auto",
            "originator_conversation_id": "manual-will-be-ignored",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["originator_conversation_id"] == ""
