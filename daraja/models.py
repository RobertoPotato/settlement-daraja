from django.db import models


class DarajaTransaction(models.Model):
    TYPE_B2C = "b2c"
    TYPE_B2B = "b2b"
    TYPE_BALANCE = "balance"
    TYPE_CHOICES = [
        (TYPE_B2C, "B2C"),
        (TYPE_B2B, "B2B"),
        (TYPE_BALANCE, "Balance"),
    ]

    STATUS_SUBMITTED = "submitted"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_TIMEOUT = "timeout"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_TIMEOUT, "Timeout"),
    ]

    transaction_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    command_id = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )
    amount = models.PositiveBigIntegerField(null=True, blank=True)
    party_a = models.CharField(max_length=64, blank=True)
    party_b = models.CharField(max_length=64, blank=True)
    account_reference = models.CharField(max_length=128, blank=True)
    remarks = models.CharField(max_length=255, blank=True)
    occasion = models.CharField(max_length=255, blank=True)
    conversation_id = models.CharField(max_length=128, blank=True, db_index=True)
    originator_conversation_id = models.CharField(max_length=128, blank=True, db_index=True)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    callback_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.transaction_type}:{self.command_id}:{self.status}"


class DarajaRequestLog(models.Model):
    transaction = models.ForeignKey(
        DarajaTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_logs",
    )
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=16, default="POST")
    request_payload = models.JSONField(default=dict)
    response_status_code = models.IntegerField(null=True, blank=True)
    response_payload = models.JSONField(default=dict)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.method} {self.endpoint} ({self.response_status_code})"


class DarajaCallbackLog(models.Model):
    CALLBACK_B2C_RESULT = "b2c_result"
    CALLBACK_B2C_TIMEOUT = "b2c_timeout"
    CALLBACK_B2B_RESULT = "b2b_result"
    CALLBACK_B2B_TIMEOUT = "b2b_timeout"
    CALLBACK_BALANCE_RESULT = "balance_result"
    CALLBACK_BALANCE_TIMEOUT = "balance_timeout"

    CALLBACK_CHOICES = [
        (CALLBACK_B2C_RESULT, "B2C Result"),
        (CALLBACK_B2C_TIMEOUT, "B2C Timeout"),
        (CALLBACK_B2B_RESULT, "B2B Result"),
        (CALLBACK_B2B_TIMEOUT, "B2B Timeout"),
        (CALLBACK_BALANCE_RESULT, "Balance Result"),
        (CALLBACK_BALANCE_TIMEOUT, "Balance Timeout"),
    ]

    transaction = models.ForeignKey(
        DarajaTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="callback_logs",
    )
    callback_type = models.CharField(max_length=32, choices=CALLBACK_CHOICES)
    payload = models.JSONField(default=dict)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True)
    conversation_id = models.CharField(max_length=128, blank=True, db_index=True)
    originator_conversation_id = models.CharField(max_length=128, blank=True, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.callback_type}:{self.result_code}"


class DarajaUITestRun(models.Model):
    TEST_B2C = "b2c"
    TEST_B2B = "b2b"
    TEST_BALANCE = "balance"
    TEST_TYPE_CHOICES = [
        (TEST_B2C, "B2C Withdrawal"),
        (TEST_B2B, "B2B Withdrawal"),
        (TEST_BALANCE, "Balance Check"),
    ]

    STATUS_SUBMITTED = "submitted"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_ERROR, "Error"),
    ]
    ENVIRONMENT_CHOICES = [
        ("sandbox", "Sandbox"),
        ("production", "Production"),
    ]

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daraja_ui_test_runs",
    )
    test_type = models.CharField(max_length=16, choices=TEST_TYPE_CHOICES)
    execution_environment = models.CharField(
        max_length=16,
        choices=ENVIRONMENT_CHOICES,
        default="sandbox",
    )
    test_status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    status_interpretation = models.TextField(blank=True)
    response_status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    transaction = models.ForeignKey(
        DarajaTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ui_test_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.test_type}:{self.test_status}:{self.created_at.isoformat()}"
