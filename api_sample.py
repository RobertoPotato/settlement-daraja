"""
Daraja Payout Manager
Handles M-Pesa B2C (to phone) and B2B (to paybill/bank) payouts
with account balance checks before disbursement.
"""

import base64
import json
import logging
from datetime import datetime

import requests

SANDBOX_CERT = b"""-----BEGIN CERTIFICATE-----
MIIGgDCCBWigAwIBAgIKMvrulAAAAARG5DANBgkqhkiG9w0BAQsFADBbMRMwEQYK
CZImiZPyLGQBGRYDbmV0MRkwFwYKCZImiZPyLGQBGRYJc2FmYXJpY29tMSkwJwYD
VQQDEyBTYWZhcmljb20gSW50ZXJuYWwgSXNzdWluZyBDQSAwMjAeFw0xNDExMTIw
NzEyNDVaFw0xNjExMTEwNzEyNDVaMHsxCzAJBgNVBAYTAktFMRAwDgYDVQQIEwdO
YWlyb2JpMRAwDgYDVQQHEwdOYWlyb2JpMRAwDgYDVQQKEwdOYWlyb2JpMRMwEQYD
VQQLEwpUZWNobm9sb2d5MSEwHwYDVQQDExhhcGljcnlwdC5zYWZhcmljb20uY28u
a2UwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCotwV1VxXsd0Q6i2w0
ugw+EPvgJfV6PNyB826Ik3L2lPJLFuzNEEJbGaiTdSe6Xitf/PJUP/q8Nv2dupHL
BkiBHjpQ6f61He8Zdc9fqKDGBLoNhNpBXxbznzI4Yu6hjBGLnF5Al9zMAxTij6wL
GUFswKpizifNbzV+LyIXY4RR2t8lxtqaFKeSx2B8P+eiZbL0wRIDPVC5+s4GdpFf
Y3QIqyLxI2bOyCGl8/XlUuIhVXxhc8Uq132xjfsWljbw4oaMobnB2KN79vMUvyoR
w8OGpga5VoaSFfVuQjSIf5RwW1hitm/8XJvmNEdeY0uKriYwbR8wfwQ3E0AIW1Fl
MMghAgMBAAGjggMkMIIDIDAdBgNVHQ4EFgQUwUfE+NgGndWDN3DyVp+CAiF1Zkgw
HwYDVR0jBBgwFoAU6zLUT35gmjqYIGO6DV6+6HlO1SQwggE7BgNVHR8EggEyMIIB
LjCCASqgggEmoIIBIoaB1mxkYXA6Ly8vQ049U2FmYXJpY29tJTIwSW50ZXJuYWwl
MjBJc3N1aW5nJTIwQ0ElMjAwMixDTj1TVkRUM0lTU0NBMDEsQ049Q0RQLENOPVB1
YmxpYyUyMEtleSUyMFNlcnZpY2VzLENOPVNlcnZpY2VzLENOPUNvbmZpZ3VyYXRp
b24sREM9c2FmYXJpY29tLERDPW5ldD9jZXJ0aWZpY2F0ZVJldm9jYXRpb25MaXN0
P2Jhc2U/b2JqZWN0Q2xhc3M9Y1JMRGlzdHJpYnV0aW9uUG9pbnSGR2h0dHA6Ly9j
cmwuc2FmYXJpY29tLmNvLmtlL1NhZmFyaWNvbSUyMEludGVybmFsJTIwSXNzdWlu
ZyUyMENBJTIwMDIuY3JsMIIBCQYIKwYBBQUHAQEEgfwwgfkwgckGCCsGAQUFBzAC
hoG8bGRhcDovLy9DTj1TYWZhcmljb20lMjBJbnRlcm5hbCUyMElzc3VpbmclMjBD
QSUyMDAyLENOPUFJQSxDTj1QdWJsaWMlMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2
aWNlcyxDTj1Db25maWd1cmF0aW9uLERDPXNhZmFyaWNvbSxEQz1uZXQ/Y0FDZXJ0
aWZpY2F0ZT9iYXNlP29iamVjdENsYXNzPWNlcnRpZmljYXRpb25BdXRob3JpdHkw
KwYIKwYBBQUHMAGGH2h0dHA6Ly9jcmwuc2FmYXJpY29tLmNvLmtlL29jc3AwCwYD
VR0PBAQDAgWgMD0GCSsGAQQBgjcVBwQwMC4GJisGAQQBgjcVCIfPjFaEwsQDhemF
NoTe0Q2GoIgIZ4bBx2yDublrAgFkAgEMMB0GA1UdJQQWMBQGCCsGAQUFBwMCBggr
BgEFBQcDATAnBgkrBgEEAYI3FQoEGjAYMAoGCCsGAQUFBwMCMAoGCCsGAQUFBwMB
MA0GCSqGSIb3DQEBCwUAA4IBAQBMFKlncYDI06ziR0Z0/reptIJRCMo+rqo/cUuP
KMmJCY3sXxFHs5ilNXo8YavgRLpxJxdZMkiUIVuVaBanXkz9/nMriiJJwwcMPjUV
9nQqwNUEqrSx29L1ARFdUy7LhN4NV7mEMde3MQybCQgBjjOPcVSVZXnaZIggDYIU
w4THLy9rDmUIasC8GDdRcVM8xDOVQD/Pt5qlx/LSbTNe2fekhTLFIGYXJVz2rcsj
k1BfG7P3pXnsPAzu199UZnqhEF+y/0/nNpf3ftHZjfX6Ws+dQuLoDN6pIl8qmok9
9E/EAgL1zOIzFvCRYlnjKdnsuqL1sIYFBlv3oxo6W1O+X9IZ
-----END CERTIFICATE-----"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DarajaPayoutManager:
    """
    A manager class for handling M-Pesa payouts via Safaricom Daraja APIs.

    Supports:
    - B2C: Send money from paybill to a customer's phone number
    - B2B: Send money from paybill to another paybill (e.g. a bank)
    - Account Balance: Query current paybill balance before payout

    Usage:
        manager = DarajaPayoutManager(
            consumer_key="your_consumer_key",
            consumer_secret="your_consumer_secret",
            shortcode="your_paybill_number",
            initiator_name="your_initiator_name",
            initiator_password="your_initiator_password",
            b2c_result_url="https://yourdomain.com/b2c/result",
            b2c_timeout_url="https://yourdomain.com/b2c/timeout",
            b2b_result_url="https://yourdomain.com/b2b/result",
            b2b_timeout_url="https://yourdomain.com/b2b/timeout",
            balance_result_url="https://yourdomain.com/balance/result",
            balance_timeout_url="https://yourdomain.com/balance/timeout",
            environment="sandbox",  # or "production"
        )
    """

    SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

    # B2B command IDs
    B2B_BUSINESS_TO_BUSINESS = "BusinessToBusinessTransfer"  # Paybill to Paybill
    B2B_BUSINESS_PAY_BILL = "BusinessPayBill"                # Paybill to Bank/Utility
    B2B_BUSINESS_BUY_GOODS = "BusinessBuyGoods"              # Paybill to Till

    # B2C command IDs
    B2C_SALARY_PAYMENT = "SalaryPayment"
    B2C_BUSINESS_PAYMENT = "BusinessPayment"
    B2C_PROMOTION_PAYMENT = "PromotionPayment"

    # Identifier types
    IDENTIFIER_MSISDN = "1"       # Phone number (B2C)
    IDENTIFIER_TILL = "2"         # Till number
    IDENTIFIER_PAYBILL = "4"      # Paybill / Organization shortcode

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        shortcode: str,
        initiator_name: str,
        initiator_password: str,
        b2c_result_url: str,
        b2c_timeout_url: str,
        b2b_result_url: str,
        b2b_timeout_url: str,
        balance_result_url: str,
        balance_timeout_url: str,
        environment: str = "sandbox",
    ):
        """
        Args:
            consumer_key:           Your Daraja app's Consumer Key.
            consumer_secret:        Your Daraja app's Consumer Secret.
            shortcode:              Your paybill/shortcode number (sender).
            initiator_name:         The M-Pesa API operator/initiator username.
            initiator_password:     The initiator's plaintext password (will be
                                    encrypted internally using Safaricom's public key).
            b2c_result_url:         HTTPS callback URL for B2C results.
            b2c_timeout_url:        HTTPS callback URL for B2C timeouts.
            b2b_result_url:         HTTPS callback URL for B2B results.
            b2b_timeout_url:        HTTPS callback URL for B2B timeouts.
            balance_result_url:     HTTPS callback URL for balance query results.
            balance_timeout_url:    HTTPS callback URL for balance query timeouts.
            environment:            "sandbox" or "production".
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.initiator_name = initiator_name
        self.initiator_password = initiator_password
        self.b2c_result_url = b2c_result_url
        self.b2c_timeout_url = b2c_timeout_url
        self.b2b_result_url = b2b_result_url
        self.b2b_timeout_url = b2b_timeout_url
        self.balance_result_url = balance_result_url
        self.balance_timeout_url = balance_timeout_url

        if environment not in ("sandbox", "production"):
            raise ValueError("environment must be 'sandbox' or 'production'")

        self.base_url = (
            self.SANDBOX_BASE_URL
            if environment == "sandbox"
            else self.PRODUCTION_BASE_URL
        )
        self._access_token: str | None = None

    # ------------------------------------------------------------------ #
    #  Internal Helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_access_token(self) -> str:
        """Fetch and cache an OAuth access token."""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        response = requests.get(
            url, headers={"Authorization": f"Basic {credentials}"}, timeout=30
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        logger.info("Access token refreshed.")
        return self._access_token

    @property
    def _auth_headers(self) -> dict:
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _encrypt_initiator_password(self) -> str:
        """
        Encrypt the initiator password using Safaricom's public certificate.

        For sandbox: uses the sandbox certificate shipped with Daraja docs.
        For production: you must download the production certificate from
        https://developer.safaricom.co.ke/ and replace the placeholder below.

        Returns a base64-encoded encrypted security credential string.
        """
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.x509 import load_pem_x509_certificate
        except ImportError:
            raise ImportError(
                "Install 'cryptography' to auto-encrypt the initiator password:\n"
                "  pip install cryptography\n"
                "Alternatively, pre-encrypt the password manually and pass it as "
                "initiator_password."
            )

        # Sandbox certificate (PEM format). Replace with production cert when going live.
        # Download production cert from: https://developer.safaricom.co.ke/
        SANDBOX_CERT_PEM = SANDBOX_CERT
        # NOTE: The certificate above is a placeholder.
        # Obtain the actual certificate from Safaricom developer portal.

        cert = load_pem_x509_certificate(SANDBOX_CERT_PEM)
        public_key = cert.public_key()
        encrypted = public_key.encrypt(
            self.initiator_password.encode(),
            padding.PKCS1v15(),
        )
        return base64.b64encode(encrypted).decode()

    @property
    def _security_credential(self) -> str:
        return self._encrypt_initiator_password()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url, headers=self._auth_headers, json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------ #
    #  Account Balance                                                     #
    # ------------------------------------------------------------------ #

    def check_balance(self, identifier_type: str = IDENTIFIER_PAYBILL) -> dict:
        """
        Query the balance of your paybill shortcode.

        The result is delivered asynchronously to balance_result_url.

        Args:
            identifier_type: Type of the shortcode.
                             Use IDENTIFIER_PAYBILL (4) for paybills (default),
                             IDENTIFIER_TILL (2) for till numbers.

        Returns:
            dict: Daraja API acknowledgement response.

        Required API inputs:
            - Initiator           (from constructor)
            - SecurityCredential  (auto-generated from initiator_password)
            - CommandID           → "AccountBalance"
            - PartyA              → your shortcode
            - IdentifierType      → shortcode type
            - ResultURL           → balance_result_url
            - QueueTimeOutURL     → balance_timeout_url
            - Remarks             → free text description
        """
        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID": "AccountBalance",
            "PartyA": self.shortcode,
            "IdentifierType": identifier_type,
            "ResultURL": self.balance_result_url,
            "QueueTimeOutURL": self.balance_timeout_url,
            "Remarks": "Account balance query",
        }
        logger.info("Querying account balance for shortcode %s", self.shortcode)
        return self._post("/mpesa/accountbalance/v1/query", payload)

    # ------------------------------------------------------------------ #
    #  B2C — Paybill → Phone Number                                       #
    # ------------------------------------------------------------------ #

    def pay_to_phone(
        self,
        phone_number: str,
        amount: int,
        remarks: str = "Payout",
        occasion: str = "",
        command_id: str = B2C_BUSINESS_PAYMENT,
    ) -> dict:
        """
        Send money from your paybill to a customer's M-Pesa phone number (B2C).

        Args:
            phone_number:  Recipient's phone in international format, e.g. "254712345678".
            amount:        Amount in KES (whole number).
            remarks:       Short description (max 100 chars).
            occasion:      Optional additional info (max 100 chars).
            command_id:    Transaction type. One of:
                           - B2C_SALARY_PAYMENT     → for salary disbursements
                           - B2C_BUSINESS_PAYMENT   → for general payments (default)
                           - B2C_PROMOTION_PAYMENT  → for promotional payouts

        Returns:
            dict: Daraja API acknowledgement response.
                  Actual result is delivered to b2c_result_url.

        Required API inputs:
            - InitiatorName       (from constructor)
            - SecurityCredential  (auto-generated)
            - CommandID           → command_id
            - Amount              → amount
            - PartyA              → your shortcode (sender)
            - PartyB              → recipient phone number
            - Remarks             → remarks
            - QueueTimeOutURL     → b2c_timeout_url
            - ResultURL           → b2c_result_url
            - Occasion            → occasion (optional)
        """
        phone_number = self._normalize_phone(phone_number)
        payload = {
            "InitiatorName": self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID": command_id,
            "Amount": amount,
            "PartyA": self.shortcode,
            "PartyB": phone_number,
            "Remarks": remarks,
            "QueueTimeOutURL": self.b2c_timeout_url,
            "ResultURL": self.b2c_result_url,
            "Occasion": occasion,
        }
        logger.info("B2C payout of KES %s to %s", amount, phone_number)
        return self._post("/mpesa/b2c/v3/paymentrequest", payload)

    # ------------------------------------------------------------------ #
    #  B2B — Paybill → Bank Paybill / Another Paybill                    #
    # ------------------------------------------------------------------ #

    def pay_to_paybill(
        self,
        receiver_shortcode: str,
        amount: int,
        account_reference: str,
        remarks: str = "Payout",
        receiver_identifier_type: str = IDENTIFIER_PAYBILL,
        command_id: str = B2B_BUSINESS_PAY_BILL,
    ) -> dict:
        """
        Send money from your paybill to another paybill (e.g. a bank) via B2B.

        Args:
            receiver_shortcode:       Recipient paybill/till number.
            amount:                   Amount in KES (whole number).
            account_reference:        Account number at the recipient paybill
                                      (e.g. your bank account number).
            remarks:                  Short description (max 100 chars).
            receiver_identifier_type: Type of the receiver shortcode.
                                      Use IDENTIFIER_PAYBILL (4) for paybills (default),
                                      IDENTIFIER_TILL (2) for till numbers.
            command_id:               Transaction type. One of:
                                      - B2B_BUSINESS_PAY_BILL        → to paybill/bank (default)
                                      - B2B_BUSINESS_TO_BUSINESS     → inter-business transfer
                                      - B2B_BUSINESS_BUY_GOODS       → to a till number

        Returns:
            dict: Daraja API acknowledgement response.
                  Actual result is delivered to b2b_result_url.

        Required API inputs:
            - Initiator                   (from constructor)
            - SecurityCredential          (auto-generated)
            - CommandID                   → command_id
            - SenderIdentifierType        → "4" (paybill, always for your shortcode)
            - RecieverIdentifierType      → receiver_identifier_type
            - Amount                      → amount
            - PartyA                      → your shortcode
            - PartyB                      → receiver_shortcode
            - AccountReference            → account_reference
            - Remarks                     → remarks
            - QueueTimeOutURL             → b2b_timeout_url
            - ResultURL                   → b2b_result_url
        """
        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID": command_id,
            "SenderIdentifierType": self.IDENTIFIER_PAYBILL,
            "RecieverIdentifierType": receiver_identifier_type,
            "Amount": amount,
            "PartyA": self.shortcode,
            "PartyB": receiver_shortcode,
            "AccountReference": account_reference,
            "Remarks": remarks,
            "QueueTimeOutURL": self.b2b_timeout_url,
            "ResultURL": self.b2b_result_url,
        }
        logger.info(
            "B2B payout of KES %s to paybill %s (ref: %s)",
            amount, receiver_shortcode, account_reference,
        )
        return self._post("/mpesa/b2b/v1/paymentrequest", payload)

    # ------------------------------------------------------------------ #
    #  Convenience: Balance-gated Payout                                  #
    # ------------------------------------------------------------------ #

    def safe_pay_to_phone(
        self,
        phone_number: str,
        amount: int,
        remarks: str = "Payout",
        **kwargs,
    ) -> dict:
        """
        Wrapper around pay_to_phone() — placeholder for a balance-gated flow.

        NOTE: Daraja's Account Balance API is asynchronous (result comes to your
        callback URL), so a synchronous balance check before payment isn't directly
        possible with Daraja alone.  In a real system you would:
          1. Cache the latest balance from your balance_result_url webhook.
          2. Compare cached balance vs amount here before calling pay_to_phone().

        This method raises ValueError if a cached balance is available and insufficient.
        """
        raise NotImplementedError(
            "Implement a balance cache from your webhook and compare here. "
            "See docstring for guidance."
        )

    # ------------------------------------------------------------------ #
    #  Utility                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Ensure phone is in 254XXXXXXXXX format."""
        phone = phone.strip().lstrip("+")
        if phone.startswith("07") or phone.startswith("01"):
            phone = "254" + phone[1:]
        if not phone.startswith("254"):
            raise ValueError(
                f"Unrecognised phone format: {phone}. "
                "Expected 07XXXXXXXX, 01XXXXXXXX, +254XXXXXXXXX, or 254XXXXXXXXX."
            )
        return phone