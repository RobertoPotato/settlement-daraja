from django.contrib import admin

from .models import DarajaCallbackLog, DarajaRequestLog, DarajaTransaction, DarajaUITestRun


@admin.register(DarajaTransaction)
class DarajaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction_type",
        "command_id",
        "status",
        "amount",
        "conversation_id",
        "originator_conversation_id",
        "created_at",
    )
    list_filter = ("transaction_type", "status", "command_id")
    search_fields = ("conversation_id", "originator_conversation_id", "party_a", "party_b")


@admin.register(DarajaRequestLog)
class DarajaRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "endpoint", "method", "response_status_code", "success", "created_at")
    list_filter = ("success", "method", "endpoint")
    search_fields = ("endpoint",)


@admin.register(DarajaCallbackLog)
class DarajaCallbackLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "callback_type",
        "result_code",
        "conversation_id",
        "originator_conversation_id",
        "received_at",
    )
    list_filter = ("callback_type", "result_code")
    search_fields = ("conversation_id", "originator_conversation_id", "result_desc")


@admin.register(DarajaUITestRun)
class DarajaUITestRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "test_type",
        "execution_environment",
        "test_status",
        "response_status_code",
        "transaction",
        "created_at",
    )
    list_filter = ("test_type", "execution_environment", "test_status")
    search_fields = (
        "status_interpretation",
        "error_message",
        "transaction__originator_conversation_id",
        "transaction__conversation_id",
    )
