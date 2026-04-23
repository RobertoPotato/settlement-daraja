from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from .forms import B2BWithdrawalForm, B2CWithdrawalForm, BalanceCheckForm
from .models import DarajaTransaction, DarajaUITestRun
from .services import (
    DarajaAPIError,
    DarajaConfigurationError,
    get_daraja_manager_for_environment,
)


def _find_transaction_from_response(response_payload: dict[str, Any]) -> DarajaTransaction | None:
    originator_conversation_id = str(response_payload.get("OriginatorConversationID", ""))
    conversation_id = str(response_payload.get("ConversationID", ""))

    return (
        DarajaTransaction.objects.filter(
            Q(originator_conversation_id=originator_conversation_id)
            | Q(conversation_id=conversation_id)
        )
        .order_by("-created_at")
        .first()
    )


def _interpret_test_status(response_payload: dict[str, Any]) -> tuple[str, str, int | None]:
    response_code_raw = response_payload.get("ResponseCode")
    try:
        response_status_code = int(response_code_raw) if response_code_raw is not None else None
    except (TypeError, ValueError):
        response_status_code = None

    if response_status_code == 0:
        return (
            DarajaUITestRun.STATUS_SUBMITTED,
            "Request accepted by Daraja. Await callback for final status (success, failed, or timeout).",
            response_status_code,
        )

    return (
        DarajaUITestRun.STATUS_FAILED,
        str(response_payload.get("ResponseDescription") or "Request rejected by Daraja."),
        response_status_code,
    )


class LandingPageView(TemplateView):
    template_name = "daraja/landing.html"


class DarajaTestHomeView(LoginRequiredMixin, View):
    template_name = "daraja/home.html"

    def get(self, request, *args, **kwargs):
        context = self._build_context()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        test_type = request.POST.get("test_type", "")
        context = self._build_context()

        if test_type == DarajaUITestRun.TEST_B2C:
            form = B2CWithdrawalForm(request.POST)
            context["b2c_form"] = form
            if not form.is_valid():
                messages.error(request, "Please fix the B2C form errors and try again.")
                return render(request, self.template_name, context)
            self._execute_b2c_test(request, form.cleaned_data)
            return redirect("home")

        if test_type == DarajaUITestRun.TEST_B2B:
            form = B2BWithdrawalForm(request.POST)
            context["b2b_form"] = form
            if not form.is_valid():
                messages.error(request, "Please fix the B2B form errors and try again.")
                return render(request, self.template_name, context)
            self._execute_b2b_test(request, form.cleaned_data)
            return redirect("home")

        if test_type == DarajaUITestRun.TEST_BALANCE:
            form = BalanceCheckForm(request.POST)
            context["balance_form"] = form
            if not form.is_valid():
                messages.error(request, "Please fix the balance form errors and try again.")
                return render(request, self.template_name, context)
            self._execute_balance_test(request, form.cleaned_data)
            return redirect("home")

        messages.error(request, "Unknown test type submitted.")
        return render(request, self.template_name, context)

    def _build_context(self) -> dict[str, Any]:
        return {
            "b2c_form": B2CWithdrawalForm(),
            "b2b_form": B2BWithdrawalForm(),
            "balance_form": BalanceCheckForm(),
            "recent_test_runs": DarajaUITestRun.objects.select_related("transaction", "user")[:20],
        }

    def _save_success(
        self,
        *,
        request,
        test_type: str,
        environment: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        status, interpretation, response_status_code = _interpret_test_status(response_payload)
        transaction = _find_transaction_from_response(response_payload)

        DarajaUITestRun.objects.create(
            user=request.user,
            test_type=test_type,
            execution_environment=environment,
            test_status=status,
            status_interpretation=interpretation,
            response_status_code=response_status_code,
            request_payload=request_payload,
            response_payload=response_payload,
            transaction=transaction,
        )

        messages.success(request, f"{test_type.upper()} test sent. {interpretation}")

    def _save_error(
        self,
        *,
        request,
        test_type: str,
        environment: str,
        request_payload: dict[str, Any],
        exc: Exception,
    ) -> None:
        DarajaUITestRun.objects.create(
            user=request.user,
            test_type=test_type,
            execution_environment=environment,
            test_status=DarajaUITestRun.STATUS_ERROR,
            status_interpretation="Test run failed before Daraja accepted the request.",
            error_message=str(exc),
            request_payload=request_payload,
            response_payload={},
        )
        messages.error(request, f"{test_type.upper()} test failed: {exc}")

    def _execute_b2c_test(self, request, data: dict[str, Any]) -> None:
        environment = data["environment"]
        request_payload = {
            "environment": environment,
            "phone_number": data["phone_number"],
            "amount": str(data["amount"]),
            "remarks": data.get("remarks", ""),
            "occasion": data.get("occasion", ""),
            "command_id": data["command_id"],
        }

        try:
            manager = get_daraja_manager_for_environment(environment)
            response_payload = manager.pay_to_phone(
                phone_number=data["phone_number"],
                amount=int(data["amount"]),
                remarks=data.get("remarks", ""),
                occasion=data.get("occasion", ""),
                command_id=data["command_id"],
            )
            self._save_success(
                request=request,
                test_type=DarajaUITestRun.TEST_B2C,
                environment=environment,
                request_payload=request_payload,
                response_payload=response_payload,
            )
        except (ValueError, DarajaConfigurationError, DarajaAPIError) as exc:
            self._save_error(
                request=request,
                test_type=DarajaUITestRun.TEST_B2C,
                environment=environment,
                request_payload=request_payload,
                exc=exc,
            )

    def _execute_b2b_test(self, request, data: dict[str, Any]) -> None:
        environment = data["environment"]
        request_payload = {
            "environment": environment,
            "receiver_shortcode": data["receiver_shortcode"],
            "amount": str(data["amount"]),
            "account_reference": data["account_reference"],
            "remarks": data.get("remarks", ""),
            "receiver_identifier_type": data["receiver_identifier_type"],
            "command_id": data["command_id"],
        }

        try:
            manager = get_daraja_manager_for_environment(environment)
            response_payload = manager.pay_to_paybill(
                receiver_shortcode=data["receiver_shortcode"],
                amount=int(data["amount"]),
                account_reference=data["account_reference"],
                remarks=data.get("remarks", ""),
                receiver_identifier_type=data["receiver_identifier_type"],
                command_id=data["command_id"],
            )
            self._save_success(
                request=request,
                test_type=DarajaUITestRun.TEST_B2B,
                environment=environment,
                request_payload=request_payload,
                response_payload=response_payload,
            )
        except (ValueError, DarajaConfigurationError, DarajaAPIError) as exc:
            self._save_error(
                request=request,
                test_type=DarajaUITestRun.TEST_B2B,
                environment=environment,
                request_payload=request_payload,
                exc=exc,
            )

    def _execute_balance_test(self, request, data: dict[str, Any]) -> None:
        environment = data["environment"]
        request_payload = {
            "environment": environment,
            "identifier_type": data["identifier_type"],
        }

        try:
            manager = get_daraja_manager_for_environment(environment)
            response_payload = manager.check_balance(identifier_type=data["identifier_type"])
            self._save_success(
                request=request,
                test_type=DarajaUITestRun.TEST_BALANCE,
                environment=environment,
                request_payload=request_payload,
                response_payload=response_payload,
            )
        except (ValueError, DarajaConfigurationError, DarajaAPIError) as exc:
            self._save_error(
                request=request,
                test_type=DarajaUITestRun.TEST_BALANCE,
                environment=environment,
                request_payload=request_payload,
                exc=exc,
            )


