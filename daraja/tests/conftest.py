import pytest
from django.test import override_settings


@pytest.fixture
def daraja_config_override():
    config = {
        "environment": "sandbox",
        "consumer_key": "consumer-key",
        "consumer_secret": "consumer-secret",
        "shortcode": "600111",
        "initiator_name": "testapi",
        "initiator_password": "super-secret-password",
        "certificate_path": "/home/bob/Documents/GitHub/settlement/security/SandboxCertificate.cer",
        "callback_urls": {
            "b2c_result": "https://example.com/api/daraja/b2c/callback/result/",
            "b2c_timeout": "https://example.com/api/daraja/b2c/callback/timeout/",
            "b2b_result": "https://example.com/api/daraja/b2b/callback/result/",
            "b2b_timeout": "https://example.com/api/daraja/b2b/callback/timeout/",
            "balance_result": "https://example.com/api/daraja/balance/callback/result/",
            "balance_timeout": "https://example.com/api/daraja/balance/callback/timeout/",
        },
        "timeout_seconds": 30,
        "token_refresh_buffer_seconds": 60,
    }
    with override_settings(DARAJA_CONFIG=config):
        yield config
