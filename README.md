# Daraja M-Pesa Integration for Django

A production-ready Django integration for **Safaricom Daraja M-Pesa API**, supporting **B2C payouts** (to phone), **B2B payouts** (to paybill/bank), and **account balance** checks with environment-driven sandbox/production switching, webhook callback handling, and full audit logging.

## Features

✅ **Multiple Payout Types**
- B2C: Pay to phone numbers with support for SalaryPayment, BusinessPayment, PromotionPayment
- B2B: Pay to paybill/bank accounts with BusinessPayBill or BusinessToBusinessTransfer
- Balance: Query account balance asynchronously via callback

✅ **Environment Management**
- Sandbox and production credential switching via `DARAJA_ENV` env var
- Separate credential sets for each environment (DARAJA_SANDBOX_*, DARAJA_PRODUCTION_*)
- Certificate-based initiator password encryption using X.509

✅ **Request/Response Logging**
- Full audit trail of all outbound API calls (DarajaRequestLog)
- Full audit trail of all inbound callbacks (DarajaCallbackLog)
- Transaction lifecycle tracking (DarajaTransaction)
- JSON payload persistence for compliance and debugging

✅ **OAuth Token Management**
- Automatic token caching with expiry detection
- Configurable refresh buffer to prevent token expiry race conditions
- Transparent token refresh on subsequent requests

✅ **Callback Webhook Handling**
- CSRF-exempt webhook endpoints for Daraja callbacks
- Support for 6 callback types: B2C result/timeout, B2B result/timeout, Balance result/timeout
- Automatic transaction status transitions (submitted → success/failed/timeout)
- Conversation ID-based payload linking

✅ **Secured API Endpoints** (Django REST Framework)
- Requires user authentication (`@login_required`)
- Four endpoints: pay-to-phone, pay-to-paybill, check-balance, transaction-status
- Input validation via DRF Serializers
- Standardized JSON request/response format

✅ **Django Admin Integration**
- Operational dashboards for transactions, request logs, and callback logs
- Filtering by transaction type, status, command ID
- Search by conversation IDs, phone numbers, paybill codes

✅ **Testing**
- Pytest unit test suite with mocked HTTP responses (no live API calls)
- Test database isolation and fixture-based config override
- 100% manager and callback logic coverage

## Quick Start

### 1. Installation

```bash
# Copy requirements.txt and install dependencies
pip install -r requirements.txt

# Copy and configure .env file
cp .env.example .env
# Edit .env with sandbox credentials (see Configuration below)

# Run migrations
python manage.py makemigrations daraja
python manage.py migrate daraja

# Create a superuser for Django admin
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### 2. Configuration

Create a `.env` file in the project root with the following structure:

```env
# Django settings
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Daraja environment selection (sandbox or production)
DARAJA_ENV=sandbox

# Callback URL (must be publicly accessible; use ngrok for local development)
DARAJA_CALLBACK_BASE_URL=https://your-public-callback-domain.example

# Timeout settings (seconds)
DARAJA_TIMEOUT_SECONDS=30
DARAJA_TOKEN_REFRESH_BUFFER_SECONDS=60

# SANDBOX CREDENTIALS
DARAJA_SANDBOX_CONSUMER_KEY=your_sandbox_consumer_key
DARAJA_SANDBOX_CONSUMER_SECRET=your_sandbox_consumer_secret
DARAJA_SANDBOX_SHORTCODE=600980  # or your sandbox shortcode
DARAJA_SANDBOX_INITIATOR_NAME=your_initiator_name
DARAJA_SANDBOX_INITIATOR_PASSWORD=your_initiator_password
DARAJA_SANDBOX_CERTIFICATE_PATH=security/SandboxCertificate.cer

# PRODUCTION CREDENTIALS
DARAJA_PRODUCTION_CONSUMER_KEY=your_production_consumer_key
DARAJA_PRODUCTION_CONSUMER_SECRET=your_production_consumer_secret
DARAJA_PRODUCTION_SHORTCODE=your_production_shortcode
DARAJA_PRODUCTION_INITIATOR_NAME=your_initiator_name
DARAJA_PRODUCTION_INITIATOR_PASSWORD=your_initiator_password
DARAJA_PRODUCTION_CERTIFICATE_PATH=security/ProductionCertificate.cer
```

#### Environment Variables Reference

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DARAJA_ENV` | Active environment (sandbox or production) | `sandbox` | Yes |
| `DARAJA_CALLBACK_BASE_URL` | Public HTTPS URL for webhook callbacks | `https://api.example.com` | Yes |
| `DARAJA_TIMEOUT_SECONDS` | HTTP request timeout | `30` | No (default: 30) |
| `DARAJA_TOKEN_REFRESH_BUFFER_SECONDS` | Seconds before token expiry to trigger refresh | `60` | No (default: 60) |
| `DARAJA_SANDBOX_CONSUMER_KEY` | OAuth consumer key (sandbox) | `ABC123...` | Yes (sandbox) |
| `DARAJA_SANDBOX_CONSUMER_SECRET` | OAuth consumer secret (sandbox) | `XYZ789...` | Yes (sandbox) |
| `DARAJA_SANDBOX_SHORTCODE` | Sender shortcode (sandbox) | `600980` | Yes (sandbox) |
| `DARAJA_SANDBOX_INITIATOR_NAME` | API initiator name (sandbox) | `testuser` | Yes (sandbox) |
| `DARAJA_SANDBOX_INITIATOR_PASSWORD` | API initiator password (sandbox) | `Safaricom123!` | Yes (sandbox) |
| `DARAJA_SANDBOX_CERTIFICATE_PATH` | Path to certificate file (sandbox) | `security/SandboxCertificate.cer` | Yes (sandbox) |

(Repeat PRODUCTION_* variants for production environment)

#### Certificate Setup

1. Download certificates from Daraja portal:
   - Sandbox: SandboxCertificate.cer
   - Production: ProductionCertificate.cer

2. Place in `security/` directory:
   ```bash
   security/
   ├── SandboxCertificate.cer
   └── ProductionCertificate.cer
   ```

3. Update `.env` with correct paths

### 3. Django Admin Access

Access the admin dashboard at `/admin/` with your superuser credentials:

- **DarajaTransaction**: View all payouts (B2C, B2B, balance queries)
- **DarajaRequestLog**: Audit trail of API calls
- **DarajaCallbackLog**: Audit trail of incoming webhooks

---

## API Reference

### Core Manager Methods (Direct Usage)

Used when integrating directly from your business logic (non-API usage).

#### DarajaPayoutManager

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `pay_to_phone()` | `phone_number` (str), `amount` (Decimal), `remarks` (str, opt), `occasion` (str, opt), `command_id` (str, opt) | dict | Initiate B2C payout to phone number. Phone normalized to 254XX format. Returns Daraja response with ConversationID. |
| `pay_to_paybill()` | `receiver_shortcode` (str), `amount` (Decimal), `account_reference` (str, opt), `remarks` (str, opt), `receiver_identifier_type` (str, opt), `command_id` (str, opt) | dict | Initiate B2B payout to paybill/bank. Returns Daraja response with ConversationID. |
| `check_balance()` | `identifier_type` (str, opt) | dict | Query account balance asynchronously. Result delivered to callback URL. |
| `_get_access_token()` | None | str | Fetch and cache OAuth token. Automatically called before API requests. Token cached with expiry buffer. |
| `_get_security_credential()` | None | str | Encrypt initiator password using certificate. Cached after first call. |
| `_validate()` | None | None (raises on error) | Validate all required configuration present. Raises DarajaConfigurationError if missing. |

#### Factory Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_daraja_config()` | None | DarajaConfig | Load and return DarajaConfig from Django settings. Reads DARAJA_CONFIG dict. |
| `get_daraja_manager()` | None | DarajaPayoutManager | Instantiate DarajaPayoutManager with active config (determined by DARAJA_ENV). |

### REST API Endpoints (Secured)

Require `@login_required` authentication. All endpoints accept POST requests with JSON bodies.

#### 1. Pay to Phone (B2C)

**Endpoint**: `POST /api/daraja/pay-to-phone/`

**Authentication**: Required (user must be logged in)

**Request Body**:
```json
{
    "phone_number": "0712345678",
    "amount": "100.50",
    "remarks": "Salary payment",
    "occasion": "Monthly salary",
    "command_id": "BusinessPayment"
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `phone_number` | string | Yes | Phone number (formats: 07XX..., +254XX..., or 254XX...) |
| `amount` | decimal | Yes | Amount in KES (minimum 1 KES) |
| `remarks` | string | No | Transaction remarks/description (max 500 chars) |
| `occasion` | string | No | Transaction occasion (max 500 chars) |
| `command_id` | string | No | Daraja command ID (default: BusinessPayment). Options: SalaryPayment, BusinessPayment, PromotionPayment |

**Success Response** (HTTP 201):
```json
{
    "originator_conversation_id": "abc-123-def",
    "conversation_id": "def-456-ghi",
    "status": "submitted",
    "response_code": "0",
    "response_description": "Accept the service request successfully.",
    "message": "B2C payout initiated successfully. Track with originator_conversation_id."
}
```

**Error Response** (HTTP 400/500):
```json
{
    "error": "validation_error",
    "message": "Phone number is required"
}
```

---

#### 2. Pay to Paybill (B2B)

**Endpoint**: `POST /api/daraja/pay-to-paybill/`

**Authentication**: Required (user must be logged in)

**Request Body**:
```json
{
    "receiver_shortcode": "600222",
    "amount": "1000.00",
    "account_reference": "INV-2024-001",
    "remarks": "Payment for invoice",
    "receiver_identifier_type": "4",
    "command_id": "BusinessToBusinessTransfer"
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `receiver_shortcode` | string | Yes | Paybill or bank code (6 digits) |
| `amount` | decimal | Yes | Amount in KES (minimum 1 KES) |
| `account_reference` | string | No | Account reference/invoice number at receiver (max 500 chars) |
| `remarks` | string | No | Transaction remarks/description (max 500 chars) |
| `receiver_identifier_type` | string | No | Identifier type (default: 4). Options: 4 (shortcode), 1 (msisdn) |
| `command_id` | string | No | Daraja command ID (default: BusinessToBusinessTransfer). Options: BusinessPayBill, BusinessToBusinessTransfer |

**Success Response** (HTTP 201):
```json
{
    "originator_conversation_id": "abc-123-def",
    "conversation_id": "def-456-ghi",
    "status": "submitted",
    "response_code": "0",
    "response_description": "Accept the service request successfully.",
    "message": "B2B payout initiated successfully. Track with originator_conversation_id."
}
```

---

#### 3. Check Balance

**Endpoint**: `POST /api/daraja/check-balance/`

**Authentication**: Required (user must be logged in)

**Request Body**:
```json
{
    "identifier_type": "4"
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `identifier_type` | string | No | Identifier type (default: 4). Options: 4 (shortcode), 1 (msisdn) |

**Success Response** (HTTP 201):
```json
{
    "originator_conversation_id": "abc-123-def",
    "conversation_id": "def-456-ghi",
    "status": "submitted",
    "response_code": "0",
    "response_description": "Accept the service request successfully.",
    "message": "Balance query initiated. Result will be delivered to callback URL."
}
```

**Note**: Balance result is delivered asynchronously via callback webhook to the configured callback URL.

---

#### 4. Transaction Status

**Endpoint**: `GET /api/daraja/transaction-status/?originator_conversation_id=abc-123-def`

**Authentication**: Required (user must be logged in)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `originator_conversation_id` | string | Yes* | Daraja originator conversation ID |
| `conversation_id` | string | Yes* | Daraja conversation ID |

*At least one of `originator_conversation_id` or `conversation_id` is required

**Success Response** (HTTP 200):
```json
{
    "id": 1,
    "transaction_type": "b2c",
    "command_id": "BusinessPayment",
    "status": "success",
    "amount": "100.50",
    "party_a": "600980",
    "party_b": "254712345678",
    "account_reference": null,
    "conversation_id": "def-456-ghi",
    "originator_conversation_id": "abc-123-def",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:31:45Z"
}
```

**Error Response** (HTTP 404):
```json
{
    "error": "not_found",
    "message": "Transaction not found"
}
```

---

## Sample Usage

### Option 1: Direct Manager Usage (Service Code)

Use this approach when integrating from business logic or background tasks.

#### B2C Payout

```python
from daraja.services import get_daraja_manager

# Get manager instance (reads config from Django settings)
manager = get_daraja_manager()

# Initiate B2C payout
try:
    response = manager.pay_to_phone(
        phone_number="0712345678",
        amount=100.50,
        remarks="Salary payment",
        occasion="Monthly salary",
        command_id="BusinessPayment"  # optional
    )
    
    # Response contains Daraja API response
    originator_conversation_id = response.get("OriginatorConversationID")
    print(f"Payout initiated: {originator_conversation_id}")
    
except ValueError as e:
    # Validation error (e.g., invalid phone number, amount <= 0)
    print(f"Validation error: {e}")
except Exception as e:
    # API error (e.g., network, Daraja error)
    print(f"API error: {e}")
```

#### B2B Payout

```python
from daraja.services import get_daraja_manager

manager = get_daraja_manager()

try:
    response = manager.pay_to_paybill(
        receiver_shortcode="600222",
        amount=1000.00,
        account_reference="INV-2024-001",
        remarks="Payment for invoice",
        command_id="BusinessToBusinessTransfer"  # optional
    )
    
    conversation_id = response.get("ConversationID")
    print(f"B2B payout initiated: {conversation_id}")
    
except Exception as e:
    print(f"Error: {e}")
```

#### Check Balance

```python
from daraja.services import get_daraja_manager

manager = get_daraja_manager()

try:
    response = manager.check_balance()
    
    conversation_id = response.get("ConversationID")
    print(f"Balance query initiated: {conversation_id}")
    # Result will be delivered to callback URL
    
except Exception as e:
    print(f"Error: {e}")
```

#### Track Transaction Status

```python
from daraja.models import DarajaTransaction

# Query by originator conversation ID
transaction = DarajaTransaction.objects.get(
    originator_conversation_id="abc-123-def"
)

print(f"Status: {transaction.status}")  # 'submitted', 'success', 'failed', 'timeout'
print(f"Amount: {transaction.amount}")
print(f"Phone: {transaction.party_b}")

# Access full payloads
print(f"Request: {transaction.request_payload}")
print(f"Response: {transaction.response_payload}")
print(f"Callback: {transaction.callback_payload}")
```

---

### Option 2: REST API Usage (HTTP Requests)

Use this approach when triggering operations from frontend, external systems, or internal services.

#### Authentication Setup

```python
# First, log in to get Django session cookie
curl -X POST http://localhost:8000/admin/login/ \
  -d "username=your_user&password=your_password"
```

Or use Django's `@login_required` protection which redirects to login page.

#### B2C Payout via API

```bash
curl -X POST http://localhost:8000/api/daraja/pay-to-phone/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=your_session_id" \
  -d '{
    "phone_number": "0712345678",
    "amount": "100.50",
    "remarks": "Salary payment",
    "occasion": "Monthly salary"
  }'
```

**Python Example**:
```python
import requests
import json

session = requests.Session()

# Login (obtain session cookie)
session.post(
    "http://localhost:8000/admin/login/",
    data={"username": "your_user", "password": "your_password"}
)

# Make API request (session cookie included)
response = session.post(
    "http://localhost:8000/api/daraja/pay-to-phone/",
    headers={"Content-Type": "application/json"},
    json={
        "phone_number": "0712345678",
        "amount": 100.50,
        "remarks": "Salary payment"
    }
)

print(response.json())
# Output:
# {
#     "originator_conversation_id": "abc-123-def",
#     "conversation_id": "def-456-ghi",
#     "status": "submitted",
#     "response_code": "0",
#     "response_description": "Accept the service request successfully.",
#     "message": "B2C payout initiated successfully..."
# }
```

#### B2B Payout via API

```bash
curl -X POST http://localhost:8000/api/daraja/pay-to-paybill/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=your_session_id" \
  -d '{
    "receiver_shortcode": "600222",
    "amount": "1000.00",
    "account_reference": "INV-2024-001"
  }'
```

#### Check Balance via API

```bash
curl -X POST http://localhost:8000/api/daraja/check-balance/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=your_session_id" \
  -d '{}'
```

#### Get Transaction Status via API

```bash
curl -X GET "http://localhost:8000/api/daraja/transaction-status/?originator_conversation_id=abc-123-def" \
  -H "Cookie: sessionid=your_session_id"
```

---

## Web UI (Landing + Test Console)

This project also includes a simple Tailwind-based web interface:

| Page | Route | Purpose |
|------|-------|---------|
| Landing | `/` | Public entry page with links to login/sign up |
| Login | `/accounts/login/` | django-allauth login using email + password |
| Signup | `/accounts/signup/` | Account creation with email + password validators |
| Test Console Home | `/home/` | Authenticated page to run B2C/B2B/balance tests with forms |

### Test Console Behavior

When you submit a form on `/home/`:
1. A Daraja request is executed using the manager class.
2. A `DarajaUITestRun` row is created with:
     - Full submitted request JSON
     - Full Daraja response JSON
     - Response code
     - Interpreted test status (`submitted`, `failed`, or `error`)
     - Human-readable interpretation
3. If conversation IDs are present, the run links to the corresponding `DarajaTransaction`.
4. Recent runs are displayed in-page with expandable JSON blocks.

---

## Webhook Callbacks

### Callback URL Configuration

Daraja sends callback notifications to your configured callback URL. Each callback type has a specific endpoint:

| Callback Type | Endpoint | Purpose |
|---------------|----------|---------|
| B2C Result | `/api/daraja/daraja/b2c/callback/result/` | Successful/failed B2C payout result |
| B2C Timeout | `/api/daraja/daraja/b2c/callback/timeout/` | B2C request timeout (Daraja couldn't process) |
| B2B Result | `/api/daraja/daraja/b2b/callback/result/` | Successful/failed B2B payout result |
| B2B Timeout | `/api/daraja/daraja/b2b/callback/timeout/` | B2B request timeout |
| Balance Result | `/api/daraja/daraja/balance/callback/result/` | Balance query result |
| Balance Timeout | `/api/daraja/daraja/balance/callback/timeout/` | Balance query timeout |

### Example Callback Payload (B2C Result)

```json
{
    "Result": {
        "ResultType": 0,
        "ResultCode": 0,
        "ResultDesc": "The service request has been processed successfully.",
        "OriginatorConversationID": "abc-123-def",
        "ConversationID": "def-456-ghi",
        "TransactionID": "TXN123456",
        "Amount": "100.50",
        "ReceiverParty": "254712345678",
        "B2CUtilityAccountAvailableFunds": "50000.00",
        "B2CChargesPaidAccountAvailableFunds": "25000.00",
        "B2CRecipientIsRegisteredCustomer": "Y",
        "FinancialTransactionID": "FIN123456"
    }
}
```

### Automatic Processing

When Daraja sends a callback:
1. ✅ Endpoint receives the webhook (CSRF-exempt)
2. ✅ JSON payload parsed
3. ✅ Transaction looked up by `OriginatorConversationID` or `ConversationID`
4. ✅ Transaction status updated to `success` (if ResultCode==0), `failed` (if non-zero), or `timeout`
5. ✅ Full callback payload stored in transaction
6. ✅ DarajaCallbackLog entry created for audit trail
7. ✅ Response sent to Daraja: `{"ResultCode": 0, "ResultDesc": "Accepted"}`

### Manual Callback Inspection

```python
from daraja.models import DarajaCallbackLog, DarajaTransaction

# View all callbacks received
callbacks = DarajaCallbackLog.objects.all().order_by('-received_at')

# View callbacks for specific transaction
transaction = DarajaTransaction.objects.get(id=1)
callbacks = transaction.darajacallbacklog_set.all()

# Check callback details
for callback in callbacks:
    print(f"Type: {callback.callback_type}")
    print(f"Result Code: {callback.result_code}")
    print(f"Payload: {callback.payload}")
```

---

## Database Models

### DarajaTransaction

Master record for each payout/balance query operation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `transaction_type` | str | b2c, b2b, or balance |
| `command_id` | str | Daraja command (BusinessPayment, BusinessPayBill, etc.) |
| `status` | str | submitted, success, failed, or timeout |
| `amount` | decimal | Transaction amount in KES |
| `party_a` | str | Sender shortcode (e.g., 600980) |
| `party_b` | str | Receiver phone/paybill |
| `account_reference` | str | For B2B: invoice or reference number |
| `remarks` | str | Transaction remarks |
| `occasion` | str | Transaction occasion |
| `conversation_id` | str | Daraja conversation ID |
| `originator_conversation_id` | str | Unique transaction identifier |
| `request_payload` | json | Full request sent to Daraja |
| `response_payload` | json | Full response from Daraja |
| `callback_payload` | json | Full callback from Daraja |
| `created_at` | datetime | Transaction created timestamp |
| `updated_at` | datetime | Last updated timestamp |

### DarajaRequestLog

Audit trail of outbound API calls.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `transaction` | FK | Link to DarajaTransaction (nullable) |
| `endpoint` | str | API endpoint called |
| `method` | str | HTTP method (POST) |
| `request_payload` | json | Full request body |
| `response_payload` | json | Full response body |
| `response_status_code` | int | HTTP status code |
| `success` | bool | True if 2xx response |
| `created_at` | datetime | Request timestamp |

### DarajaCallbackLog

Audit trail of inbound callbacks from Daraja.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `transaction` | FK | Link to DarajaTransaction (nullable) |
| `callback_type` | str | b2c_result, b2c_timeout, b2b_result, etc. |
| `payload` | json | Full callback JSON from Daraja |
| `result_code` | int | Daraja result code |
| `result_desc` | str | Daraja result description |
| `conversation_id` | str | Daraja conversation ID |
| `originator_conversation_id` | str | Daraja originator conversation ID |
| `received_at` | datetime | Callback received timestamp |

---

## Development & Testing

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=daraja

# Run specific test file
pytest daraja/tests/test_manager.py -v

# Run specific test
pytest daraja/tests/test_manager.py::test_pay_to_phone_logs_request_and_transaction -v
```

### Test Structure

- **test_manager.py**: Tests for DarajaPayoutManager (B2C, B2B, balance)
  - Mocks OAuth token endpoint
  - Mocks Daraja API endpoints
  - Verifies phone normalization, transaction creation, request logging

- **test_callbacks.py**: Tests for webhook callback handling
  - Tests B2C result/timeout callbacks
  - Tests B2B timeout callback
  - Tests balance callback
  - Verifies status transitions, payload persistence

### Adding New Tests

```python
import pytest
import responses
from daraja.services import get_daraja_manager
from daraja.models import DarajaTransaction

@pytest.mark.django_db
@responses.activate
def test_new_feature():
    # Mock OAuth endpoint
    responses.add(
        responses.GET,
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        json={"access_token": "token", "expires_in": "3599"},
        status=200,
    )
    
    # Mock Daraja endpoint
    responses.add(
        responses.POST,
        "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest",
        json={"ConversationID": "conv-001", "OriginatorConversationID": "orig-001"},
        status=200,
    )
    
    # Run test
    manager = get_daraja_manager()
    response = manager.pay_to_phone("0712345678", 100)
    
    assert response["ConversationID"] == "conv-001"
    transaction = DarajaTransaction.objects.get(originator_conversation_id="orig-001")
    assert transaction.status == DarajaTransaction.STATUS_SUBMITTED
```

---

## Environment Switching

### Development (Sandbox)

```bash
# .env
DARAJA_ENV=sandbox
DARAJA_SANDBOX_CONSUMER_KEY=your_sandbox_key
DARAJA_SANDBOX_CONSUMER_SECRET=your_sandbox_secret
# ... other sandbox credentials
```

### Production

```bash
# .env
DARAJA_ENV=production
DARAJA_PRODUCTION_CONSUMER_KEY=your_production_key
DARAJA_PRODUCTION_CONSUMER_SECRET=your_production_secret
# ... other production credentials
```

No code changes needed. The manager automatically loads credentials based on `DARAJA_ENV`.

---

## Troubleshooting

### Common Issues

**1. "DARAJA_ENV must be either 'sandbox' or 'production'"**
- Ensure `DARAJA_ENV` in `.env` is exactly `sandbox` or `production` (lowercase)

**2. "Missing required configuration: consumer_key"**
- Ensure all `DARAJA_SANDBOX_*` or `DARAJA_PRODUCTION_*` environment variables are set
- Run: `echo $DARAJA_SANDBOX_CONSUMER_KEY` to verify

**3. Certificate not found**
- Verify certificate file exists at path specified in `DARAJA_*_CERTIFICATE_PATH`
- Check file permissions (should be readable)

**4. Callback not received**
- Verify `DARAJA_CALLBACK_BASE_URL` is publicly accessible
- Use ngrok (local dev): `ngrok http 8000`, then set `DARAJA_CALLBACK_BASE_URL=https://your-ngrok-url.ngrok.io`
- Check Django logs for incoming requests
- Verify callback routes registered: `python manage.py show_urls`

**5. Token expiration errors**
- Increase `DARAJA_TOKEN_REFRESH_BUFFER_SECONDS` (default 60 seconds)
- Ensure system clock is synchronized

**6. "Database access not allowed" in tests**
- Add `@pytest.mark.django_db` decorator to test function
- Run pytest with: `pytest --ds=settlement.settings`

---

## Production Checklist

- [ ] Set `DJANGO_DEBUG=False` in production
- [ ] Update `DJANGO_SECRET_KEY` to a secure random value
- [ ] Use production M-Pesa credentials (not sandbox)
- [ ] Set `DARAJA_ENV=production`
- [ ] Configure `DARAJA_CALLBACK_BASE_URL` to production domain
- [ ] Use HTTPS for all URLs (required by Daraja)
- [ ] Set up SSL certificates
- [ ] Configure `ALLOWED_HOSTS` with production domain
- [ ] Use strong `DJANGO_SUPERUSER_PASSWORD`
- [ ] Enable Django security middleware
- [ ] Set up database backups
- [ ] Monitor logs and transaction status via admin
- [ ] Set up monitoring/alerting for failed transactions
- [ ] Test end-to-end flow with small amounts

---

## License

This integration is part of the Settlement Django project.

## Support

For issues or questions:
1. Check Django admin for transaction/callback logs
2. Review DarajaRequestLog for API call details
3. Check system logs for error messages
4. Refer to [Daraja Documentation](https://daraja.safaricom.co.ke)
