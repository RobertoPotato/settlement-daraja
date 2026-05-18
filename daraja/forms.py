from decimal import Decimal

from django import forms
from django.conf import settings

from .models import DarajaPaybillConfig, DarajaTransaction
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
    paybill_number = forms.ChoiceField(choices=[])
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        environment = self._selected_environment()
        self.fields["paybill_number"].choices = self._paybill_choices(environment)

    def _selected_environment(self) -> str:
        if self.is_bound:
            value = str(self.data.get("environment", "")).strip().lower()
            if value in {"sandbox", "production"}:
                return value
        initial = self.initial.get("environment") if isinstance(self.initial, dict) else None
        value = str(initial or _default_environment()).strip().lower()
        return value if value in {"sandbox", "production"} else "sandbox"

    @staticmethod
    def _paybill_choices(environment: str) -> list[tuple[str, str]]:
        rows = DarajaPaybillConfig.objects.filter(
            environment=environment,
            is_active=True,
        ).order_by("paybill_number")
        return [
            (row.paybill_number, f"{row.paybill_number} (Shortcode {row.shortcode})")
            for row in rows
        ]

    def clean_paybill_number(self) -> str:
        paybill_number = str(self.cleaned_data.get("paybill_number", "")).strip()
        environment = str(self.cleaned_data.get("environment", "")).strip().lower()
        exists = DarajaPaybillConfig.objects.filter(
            paybill_number=paybill_number,
            environment=environment,
            is_active=True,
        ).exists()
        if not exists:
            raise forms.ValidationError("Select a valid active paybill for this environment.")
        return paybill_number

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
    paybill_number = forms.ChoiceField(choices=[])
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        environment = self._selected_environment()
        self.fields["paybill_number"].choices = B2CWithdrawalForm._paybill_choices(environment)

    def _selected_environment(self) -> str:
        if self.is_bound:
            value = str(self.data.get("environment", "")).strip().lower()
            if value in {"sandbox", "production"}:
                return value
        initial = self.initial.get("environment") if isinstance(self.initial, dict) else None
        value = str(initial or _default_environment()).strip().lower()
        return value if value in {"sandbox", "production"} else "sandbox"

    def clean_paybill_number(self) -> str:
        paybill_number = str(self.cleaned_data.get("paybill_number", "")).strip()
        environment = str(self.cleaned_data.get("environment", "")).strip().lower()
        exists = DarajaPaybillConfig.objects.filter(
            paybill_number=paybill_number,
            environment=environment,
            is_active=True,
        ).exists()
        if not exists:
            raise forms.ValidationError("Select a valid active paybill for this environment.")
        return paybill_number


class BalanceCheckForm(forms.Form):
    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial=_default_environment,
    )
    paybill_number = forms.ChoiceField(choices=[])
    identifier_type = forms.ChoiceField(
        choices=[
            (DarajaPayoutManager.IDENTIFIER_PAYBILL, "Paybill (4)"),
            (DarajaPayoutManager.IDENTIFIER_MSISDN, "MSISDN (1)"),
        ],
        initial=DarajaPayoutManager.IDENTIFIER_PAYBILL,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        environment = self._selected_environment()
        self.fields["paybill_number"].choices = B2CWithdrawalForm._paybill_choices(environment)

    def _selected_environment(self) -> str:
        if self.is_bound:
            value = str(self.data.get("environment", "")).strip().lower()
            if value in {"sandbox", "production"}:
                return value
        initial = self.initial.get("environment") if isinstance(self.initial, dict) else None
        value = str(initial or _default_environment()).strip().lower()
        return value if value in {"sandbox", "production"} else "sandbox"

    def clean_paybill_number(self) -> str:
        paybill_number = str(self.cleaned_data.get("paybill_number", "")).strip()
        environment = str(self.cleaned_data.get("environment", "")).strip().lower()
        exists = DarajaPaybillConfig.objects.filter(
            paybill_number=paybill_number,
            environment=environment,
            is_active=True,
        ).exists()
        if not exists:
            raise forms.ValidationError("Select a valid active paybill for this environment.")
        return paybill_number


class DarajaPaybillConfigForm(forms.ModelForm):
    class Meta:
        model = DarajaPaybillConfig
        fields = [
            "paybill_number",
            "environment",
            "consumer_key",
            "consumer_secret",
            "shortcode",
            "initiator_name",
            "initiator_password",
            "is_active",
        ]
