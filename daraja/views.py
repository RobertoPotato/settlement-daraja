import json
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import DarajaCallbackLog, DarajaTransaction


def _extract_result_data(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("Result")
    if isinstance(result, dict):
        return result
    return payload


def _extract_identifiers(payload: dict[str, Any]) -> tuple[str, str]:
    result = _extract_result_data(payload)
    conversation_id = str(result.get("ConversationID", ""))
    originator_conversation_id = str(result.get("OriginatorConversationID", ""))
    return conversation_id, originator_conversation_id


def _extract_result_code(payload: dict[str, Any]) -> int | None:
    result = _extract_result_data(payload)
    code = result.get("ResultCode")
    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _extract_result_desc(payload: dict[str, Any]) -> str:
    result = _extract_result_data(payload)
    return str(result.get("ResultDesc", ""))


def _status_for_callback(callback_type: str, result_code: int | None) -> str:
    if "timeout" in callback_type:
        return DarajaTransaction.STATUS_TIMEOUT
    if result_code == 0:
        return DarajaTransaction.STATUS_SUCCESS
    return DarajaTransaction.STATUS_FAILED


@method_decorator(csrf_exempt, name="dispatch")
class BaseDarajaCallbackView(View):
    callback_type: str = ""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON payload"}, status=400)

        conversation_id, originator_conversation_id = _extract_identifiers(payload)
        result_code = _extract_result_code(payload)
        result_desc = _extract_result_desc(payload)

        transaction = (
            DarajaTransaction.objects.filter(
                originator_conversation_id=originator_conversation_id
            ).first()
            or DarajaTransaction.objects.filter(conversation_id=conversation_id).first()
        )

        if transaction:
            transaction.status = _status_for_callback(self.callback_type, result_code)
            transaction.callback_payload = payload
            transaction.save(update_fields=["status", "callback_payload", "updated_at"])

        DarajaCallbackLog.objects.create(
            transaction=transaction,
            callback_type=self.callback_type,
            payload=payload,
            result_code=result_code,
            result_desc=result_desc,
            conversation_id=conversation_id,
            originator_conversation_id=originator_conversation_id,
        )

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


class B2CResultCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_B2C_RESULT


class B2CTimeoutCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_B2C_TIMEOUT


class B2BResultCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_B2B_RESULT


class B2BTimeoutCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_B2B_TIMEOUT


class BalanceResultCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_BALANCE_RESULT


class BalanceTimeoutCallbackView(BaseDarajaCallbackView):
    callback_type = DarajaCallbackLog.CALLBACK_BALANCE_TIMEOUT
