from decimal import Decimal

from django import forms
from django.conf import settings

from .models import DarajaTransaction
from .services import DarajaPayoutManager


ENVIRONMENT_CHOICES = [
    ("sandbox", "Sandbox"),
    ("production", "Production"),
]


def _default_environment() -> str:
    value = str(getattr(settings, "DARAJA_ENV", "sandbox")).strip().lower()
    return value if value in {"sandbox", "production"} else "sandbox"


class B2CWithdrawalForm(forms.Form):
    ORIGINATOR_ID_MODE_AUTO = "auto"
    ORIGINATOR_ID_MODE_MANUAL = "manual"
    ORIGINATOR_ID_MODE_CHOICES = [
        (ORIGINATOR_ID_MODE_AUTO, "Auto-generate unique ID"),
        (ORIGINATOR_ID_MODE_MANUAL, "Enter ID manually"),
    ]

    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial=_default_environment,
    )
    phone_number = forms.CharField(max_length=20)
    amount = forms.DecimalField(min_value=Decimal("1"), decimal_places=0, max_digits=12)
    remarks = forms.CharField(max_length=255, required=False)
    occasion = forms.CharField(max_length=255, required=False)
    command_id = forms.ChoiceField(
        choices=[
            (DarajaPayoutManager.B2C_BUSINESS_PAYMENT, "BusinessPayment"),
            (DarajaPayoutManager.B2C_SALARY_PAYMENT, "SalaryPayment"),
            (DarajaPayoutManager.B2C_PROMOTION_PAYMENT, "PromotionPayment"),
        ],
        initial=DarajaPayoutManager.B2C_BUSINESS_PAYMENT,
    )
    originator_id_mode = forms.ChoiceField(
        choices=ORIGINATOR_ID_MODE_CHOICES,
        initial=ORIGINATOR_ID_MODE_AUTO,
    )
    originator_conversation_id = forms.CharField(
        max_length=128,
        required=False,
        help_text="Used only when manual mode is selected.",
    )

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get("originator_id_mode", self.ORIGINATOR_ID_MODE_AUTO)
        originator_conversation_id = str(
            cleaned_data.get("originator_conversation_id") or ""
        ).strip()

        if mode == self.ORIGINATOR_ID_MODE_MANUAL:
            if not originator_conversation_id:
                self.add_error(
                    "originator_conversation_id",
                    "OriginatorConversationID is required in manual mode.",
                )
            elif DarajaTransaction.objects.filter(
                originator_conversation_id=originator_conversation_id
            ).exists():
                self.add_error(
                    "originator_conversation_id",
                    "This OriginatorConversationID already exists. Use a different value.",
                )
        else:
            originator_conversation_id = ""

        cleaned_data["originator_conversation_id"] = originator_conversation_id
        return cleaned_data


class B2BWithdrawalForm(forms.Form):
    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial=_default_environment,
    )
    receiver_shortcode = forms.CharField(max_length=20)
    amount = forms.DecimalField(min_value=Decimal("1"), decimal_places=0, max_digits=12)
    account_reference = forms.CharField(max_length=128)
    remarks = forms.CharField(max_length=255, required=False)
    receiver_identifier_type = forms.ChoiceField(
        choices=[
            (DarajaPayoutManager.IDENTIFIER_PAYBILL, "Paybill (4)"),
            (DarajaPayoutManager.IDENTIFIER_MSISDN, "MSISDN (1)"),
        ],
        initial=DarajaPayoutManager.IDENTIFIER_PAYBILL,
    )
    command_id = forms.ChoiceField(
        choices=[
            (DarajaPayoutManager.B2B_BUSINESS_PAY_BILL, "BusinessPayBill"),
            (DarajaPayoutManager.B2B_BUSINESS_TO_BUSINESS, "BusinessToBusinessTransfer"),
            (DarajaPayoutManager.B2B_BUSINESS_BUY_GOODS, "BusinessBuyGoods"),
        ],
        initial=DarajaPayoutManager.B2B_BUSINESS_PAY_BILL,
    )


class BalanceCheckForm(forms.Form):
    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial=_default_environment,
    )
    identifier_type = forms.ChoiceField(
        choices=[
            (DarajaPayoutManager.IDENTIFIER_PAYBILL, "Paybill (4)"),
            (DarajaPayoutManager.IDENTIFIER_MSISDN, "MSISDN (1)"),
        ],
        initial=DarajaPayoutManager.IDENTIFIER_PAYBILL,
    )
