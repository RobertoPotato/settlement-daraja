import base64
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from django.conf import settings
from django.db import IntegrityError

from .models import DarajaRequestLog, DarajaTransaction

logger = logging.getLogger(__name__)


class DarajaConfigurationError(Exception):
    pass


class DarajaAPIError(Exception):
    pass


@dataclass
class DarajaConfig:
    environment: str
    consumer_key: str
    consumer_secret: str
    shortcode: str
    initiator_name: str
    initiator_password: str
    certificate_path: str
    callback_urls: dict[str, str]
    timeout_seconds: int = 30
    token_refresh_buffer_seconds: int = 60


class DarajaPayoutManager:
    SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

    B2B_BUSINESS_TO_BUSINESS = "BusinessToBusinessTransfer"
    B2B_BUSINESS_PAY_BILL = "BusinessPayBill"
    B2B_BUSINESS_BUY_GOODS = "BusinessBuyGoods"

    B2C_SALARY_PAYMENT = "SalaryPayment"
    B2C_BUSINESS_PAYMENT = "BusinessPayment"
    B2C_PROMOTION_PAYMENT = "PromotionPayment"

    IDENTIFIER_MSISDN = "1"
    IDENTIFIER_TILL = "2"
    IDENTIFIER_PAYBILL = "4"

    def __init__(self, config: DarajaConfig, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self._security_credential: str | None = None
        self.base_url = (
            self.SANDBOX_BASE_URL
            if self.config.environment == "sandbox"
            else self.PRODUCTION_BASE_URL
        )

    def _validate(self) -> None:
        required_fields = {
            "consumer_key": self.config.consumer_key,
            "consumer_secret": self.config.consumer_secret,
            "shortcode": self.config.shortcode,
            "initiator_name": self.config.initiator_name,
            "initiator_password": self.config.initiator_password,
            "certificate_path": self.config.certificate_path,
        }
        missing = [key for key, value in required_fields.items() if not value]
        if missing:
            raise DarajaConfigurationError(
                f"Missing Daraja configuration values for {', '.join(missing)}"
            )

        required_callbacks = [
            "b2c_result",
            "b2c_timeout",
            "b2b_result",
            "b2b_timeout",
            "balance_result",
            "balance_timeout",
        ]
        missing_callbacks = [
            key for key in required_callbacks if not self.config.callback_urls.get(key)
        ]
        if missing_callbacks:
            raise DarajaConfigurationError(
                "Missing Daraja callback URLs for " + ", ".join(missing_callbacks)
            )

    def _get_access_token(self) -> str:
        if self._access_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry:
                return self._access_token

        credentials = base64.b64encode(
            f"{self.config.consumer_key}:{self.config.consumer_secret}".encode("utf-8")
        ).decode("utf-8")
        response = self.session.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=self.config.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DarajaAPIError("Failed to retrieve Daraja access token") from exc

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3599))
        if not access_token:
            raise DarajaAPIError("Daraja token response missing access_token")

        refresh_margin = max(0, self.config.token_refresh_buffer_seconds)
        self._token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=max(0, expires_in - refresh_margin)
        )
        self._access_token = access_token
        return access_token

    def _get_security_credential(self) -> str:
        if self._security_credential:
            return self._security_credential

        with open(self.config.certificate_path, "rb") as cert_file:
            certificate = load_pem_x509_certificate(cert_file.read())

        public_key = certificate.public_key()
        encrypted = public_key.encrypt(
            self.config.initiator_password.encode("utf-8"),
            padding.PKCS1v15(),
        )
        self._security_credential = base64.b64encode(encrypted).decode("utf-8")
        return self._security_credential

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    def _create_transaction(self, transaction_type: str, command_id: str, payload: dict[str, Any]) -> DarajaTransaction:
        return DarajaTransaction.objects.create(
            transaction_type=transaction_type,
            command_id=command_id,
            amount=payload.get("Amount"),
            party_a=str(payload.get("PartyA", "")),
            party_b=str(payload.get("PartyB", "")),
            account_reference=str(payload.get("AccountReference", "")),
            remarks=str(payload.get("Remarks", "")),
            occasion=str(payload.get("Occasion", "")),
            originator_conversation_id=str(payload.get("OriginatorConversationID", "")),
            request_payload=payload,
        )

    @staticmethod
    def _clean_originator_conversation_id(originator_conversation_id: str) -> str:
        value = originator_conversation_id.strip()
        if not value:
            raise ValueError("OriginatorConversationID cannot be blank when provided")
        if len(value) > 128:
            raise ValueError("OriginatorConversationID must be 128 characters or fewer")
        return value

    @classmethod
    def _generate_originator_conversation_id(cls) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"b2c-{timestamp}-{uuid.uuid4().hex[:12]}"

    def _post(self, endpoint: str, payload: dict[str, Any], transaction: DarajaTransaction | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        status_code = None
        response_json: dict[str, Any] = {}

        try:
            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            status_code = response.status_code
            response_json = response.json()
            response.raise_for_status()
        except requests.RequestException as exc:
            DarajaRequestLog.objects.create(
                transaction=transaction,
                endpoint=endpoint,
                method="POST",
                request_payload=payload,
                response_status_code=status_code,
                response_payload=response_json,
                success=False,
            )
            raise DarajaAPIError(f"Daraja request failed for {endpoint}") from exc

        DarajaRequestLog.objects.create(
            transaction=transaction,
            endpoint=endpoint,
            method="POST",
            request_payload=payload,
            response_status_code=status_code,
            response_payload=response_json,
            success=True,
        )

        if transaction:
            transaction.conversation_id = response_json.get("ConversationID", "")
            transaction.originator_conversation_id = response_json.get(
                "OriginatorConversationID", ""
            )
            transaction.response_payload = response_json
            transaction.save(
                update_fields=[
                    "conversation_id",
                    "originator_conversation_id",
                    "response_payload",
                    "updated_at",
                ]
            )

        return response_json

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        cleaned = phone.strip().lstrip("+")
        if cleaned.startswith("07") or cleaned.startswith("01"):
            cleaned = f"254{cleaned[1:]}"
        if not cleaned.startswith("254") or len(cleaned) != 12:
            raise ValueError(
                "Unrecognised phone format. Use 07XXXXXXXX, 01XXXXXXXX, +254XXXXXXXXX, or 254XXXXXXXXX."
            )
        return cleaned

    @staticmethod
    def _validate_amount(amount: int) -> None:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")

    def check_balance(self, identifier_type: str = IDENTIFIER_PAYBILL) -> dict[str, Any]:
        self._validate()
        payload = {
            "Initiator": self.config.initiator_name,
            "SecurityCredential": self._get_security_credential(),
            "CommandID": "AccountBalance",
            "PartyA": self.config.shortcode,
            "IdentifierType": identifier_type,
            "ResultURL": self.config.callback_urls["balance_result"],
            "QueueTimeOutURL": self.config.callback_urls["balance_timeout"],
            "Remarks": "Account balance query",
        }
        transaction = self._create_transaction(DarajaTransaction.TYPE_BALANCE, "AccountBalance", payload)
        return self._post("/mpesa/accountbalance/v1/query", payload, transaction=transaction)

    def pay_to_phone(
        self,
        phone_number: str,
        amount: int,
        remarks: str = "Payout",
        occasion: str = "",
        command_id: str = B2C_BUSINESS_PAYMENT,
        originator_conversation_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate()
        self._validate_amount(amount)

        resolved_originator_conversation_id = (
            self._clean_originator_conversation_id(originator_conversation_id)
            if originator_conversation_id
            else ""
        )

        if resolved_originator_conversation_id and DarajaTransaction.objects.filter(
            originator_conversation_id=resolved_originator_conversation_id
        ).exists():
            raise ValueError(
                f"OriginatorConversationID '{resolved_originator_conversation_id}' already exists"
            )

        # Auto-generation retries handle very unlikely ID collisions during concurrent submissions.
        for _ in range(5):
            request_originator_conversation_id = (
                resolved_originator_conversation_id
                if resolved_originator_conversation_id
                else self._generate_originator_conversation_id()
            )

            payload = {
                "OriginatorConversationID": request_originator_conversation_id,
                "InitiatorName": self.config.initiator_name,
                "SecurityCredential": self._get_security_credential(),
                "CommandID": command_id,
                "Amount": amount,
                "PartyA": self.config.shortcode,
                "PartyB": self._normalize_phone(phone_number),
                "Remarks": remarks,
                "QueueTimeOutURL": self.config.callback_urls["b2c_timeout"],
                "ResultURL": self.config.callback_urls["b2c_result"],
                "Occasion": occasion,
            }

            try:
                transaction = self._create_transaction(
                    DarajaTransaction.TYPE_B2C,
                    command_id,
                    payload,
                )
                return self._post(
                    "/mpesa/b2c/v3/paymentrequest",
                    payload,
                    transaction=transaction,
                )
            except IntegrityError as exc:
                if resolved_originator_conversation_id:
                    raise ValueError(
                        f"OriginatorConversationID '{resolved_originator_conversation_id}' already exists"
                    ) from exc

        raise DarajaAPIError(
            "Failed to generate a unique OriginatorConversationID after multiple attempts"
        )

    def pay_to_paybill(
        self,
        receiver_shortcode: str,
        amount: int,
        account_reference: str,
        remarks: str = "Payout",
        receiver_identifier_type: str = IDENTIFIER_PAYBILL,
        command_id: str = B2B_BUSINESS_PAY_BILL,
    ) -> dict[str, Any]:
        self._validate()
        self._validate_amount(amount)

        payload = {
            "Initiator": self.config.initiator_name,
            "SecurityCredential": self._get_security_credential(),
            "CommandID": command_id,
            "SenderIdentifierType": int(self.IDENTIFIER_PAYBILL),
            "RecieverIdentifierType": int(receiver_identifier_type),
            "Requester": int("254708374149"),
            "Amount": amount,
            "PartyA": int(self.config.shortcode),
            "PartyB": int(receiver_shortcode),
            "AccountReference": account_reference,
            "Remarks": remarks,
            "QueueTimeOutURL": self.config.callback_urls["b2b_timeout"],
            "ResultURL": self.config.callback_urls["b2b_result"],
        }
        transaction = self._create_transaction(DarajaTransaction.TYPE_B2B, command_id, payload)
        return self._post("/mpesa/b2b/v1/paymentrequest", payload, transaction=transaction)


def _build_environment_config(environment: str) -> DarajaConfig:
    env = environment.strip().lower()
    if env not in {"sandbox", "production"}:
        raise DarajaConfigurationError("Environment must be 'sandbox' or 'production'.")

    prefix = f"DARAJA_{env.upper()}"
    base_dir = getattr(settings, "BASE_DIR")
    certificate_default = str(
        base_dir
        / "security"
        / ("SandboxCertificate.cer" if env == "sandbox" else "ProductionCertificate.cer")
    )

    return DarajaConfig(
        environment=env,
        consumer_key=os.getenv(f"{prefix}_CONSUMER_KEY", ""),
        consumer_secret=os.getenv(f"{prefix}_CONSUMER_SECRET", ""),
        shortcode=os.getenv(f"{prefix}_SHORTCODE", ""),
        initiator_name=os.getenv(f"{prefix}_INITIATOR_NAME", ""),
        initiator_password=os.getenv(f"{prefix}_INITIATOR_PASSWORD", ""),
        certificate_path=os.getenv(f"{prefix}_CERTIFICATE_PATH", certificate_default),
        callback_urls=getattr(settings, "DARAJA_CALLBACK_URLS", {}),
        timeout_seconds=int(getattr(settings, "DARAJA_TIMEOUT_SECONDS", 30)),
        token_refresh_buffer_seconds=int(
            getattr(settings, "DARAJA_TOKEN_REFRESH_BUFFER_SECONDS", 60)
        ),
    )


def get_daraja_config(environment: str | None = None) -> DarajaConfig:
    if environment:
        return _build_environment_config(environment)

    raw_config = getattr(settings, "DARAJA_CONFIG", {})
    callback_urls = raw_config.get("callback_urls", {})
    return DarajaConfig(
        environment=raw_config.get("environment", "sandbox"),
        consumer_key=raw_config.get("consumer_key", ""),
        consumer_secret=raw_config.get("consumer_secret", ""),
        shortcode=raw_config.get("shortcode", ""),
        initiator_name=raw_config.get("initiator_name", ""),
        initiator_password=raw_config.get("initiator_password", ""),
        certificate_path=raw_config.get("certificate_path", ""),
        callback_urls=callback_urls,
        timeout_seconds=int(raw_config.get("timeout_seconds", 30)),
        token_refresh_buffer_seconds=int(raw_config.get("token_refresh_buffer_seconds", 60)),
    )


def get_daraja_manager() -> DarajaPayoutManager:
    return DarajaPayoutManager(config=get_daraja_config())


def get_daraja_manager_for_environment(environment: str) -> DarajaPayoutManager:
    return DarajaPayoutManager(config=get_daraja_config(environment=environment))
