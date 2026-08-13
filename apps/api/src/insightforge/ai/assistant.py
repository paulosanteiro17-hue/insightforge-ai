from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import Field, model_validator

from insightforge.ai.schemas import StrictAIModel

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_INJECTION_PATTERNS = (
    re.compile(r"\b(?:ignore|disregard|override)\b.{0,50}\b(?:instructions?|prompts?|rules?)\b"),
    re.compile(r"\b(?:system|developer)\s+(?:prompt|message)\b"),
    re.compile(r"\b(?:jailbreak|prompt\s+injection|bypass\s+(?:safety|rules?))\b"),
    re.compile(r"\b(?:show|reveal|print)\b.{0,30}\b(?:prompt|instructions?|secrets?)\b"),
    re.compile(r"\b(?:execute|run)\s+(?:sql|query|code|command)\b"),
    re.compile(r"\bselect\b.{0,200}\bfrom\b"),
    re.compile(r"\b(?:drop\s+table|insert\s+into|delete\s+from|union\s+select)\b"),
    re.compile(r"\b(?:information_schema|pg_catalog)\b"),
)


class AskIntent(StrEnum):
    SALES_STATUS = "sales_status"
    TOP_PRODUCT = "top_product"
    REVENUE_DECLINE = "revenue_decline"
    TOP_CUSTOMERS = "top_customers"
    BUSINESS_SUMMARY = "business_summary"


class AskRoutingErrorCode(StrEnum):
    INVALID_QUESTION = "invalid_question"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    INVALID_PARAMETERS = "invalid_parameters"


class AskRoutingError(ValueError):
    def __init__(self, code: AskRoutingErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SalesStatusParameters(StrictAIModel):
    status: Literal["pending", "paid", "processing", "completed", "cancelled", "refunded"] | None


class TopProductParameters(StrictAIModel):
    limit: Annotated[int, Field(ge=1, le=10)] = 1


class RevenueDeclineParameters(StrictAIModel):
    comparison: Literal["previous_period"] = "previous_period"


class TopCustomersParameters(StrictAIModel):
    limit: Annotated[int, Field(ge=1, le=10)] = 5


class BusinessSummaryParameters(StrictAIModel):
    include_watch_items: Literal[True] = True


AskParameters = (
    SalesStatusParameters
    | TopProductParameters
    | RevenueDeclineParameters
    | TopCustomersParameters
    | BusinessSummaryParameters
)


class AskRoute(StrictAIModel):
    """Allowlisted intent with typed parameters; the raw question is not retained."""

    intent: AskIntent
    parameters: AskParameters

    @model_validator(mode="after")
    def parameters_match_intent(self) -> Self:
        matches = any(
            (
                self.intent is AskIntent.SALES_STATUS
                and isinstance(self.parameters, SalesStatusParameters),
                self.intent is AskIntent.TOP_PRODUCT
                and isinstance(self.parameters, TopProductParameters),
                self.intent is AskIntent.REVENUE_DECLINE
                and isinstance(self.parameters, RevenueDeclineParameters),
                self.intent is AskIntent.TOP_CUSTOMERS
                and isinstance(self.parameters, TopCustomersParameters),
                self.intent is AskIntent.BUSINESS_SUMMARY
                and isinstance(self.parameters, BusinessSummaryParameters),
            )
        )
        if not matches:
            raise ValueError("Intent parameters do not match the selected intent.")
        return self


def _normalize_question(question: str) -> str:
    if not isinstance(question, str):
        raise AskRoutingError(
            AskRoutingErrorCode.INVALID_QUESTION,
            "The question must be text.",
        )
    if _CONTROL_CHARACTERS.search(question) is not None:
        raise AskRoutingError(
            AskRoutingErrorCode.INVALID_QUESTION,
            "The question contains unsupported control characters.",
        )
    normalized = " ".join(unicodedata.normalize("NFKC", question).casefold().split())
    if len(normalized) < 3 or len(normalized) > 500:
        raise AskRoutingError(
            AskRoutingErrorCode.INVALID_QUESTION,
            "The question must contain between 3 and 500 characters.",
        )
    if any(pattern.search(normalized) is not None for pattern in _INJECTION_PATTERNS):
        raise AskRoutingError(
            AskRoutingErrorCode.BLOCKED,
            "The question contains instructions that are not allowed.",
        )
    return normalized


def _requested_limit(question: str, default: int) -> int:
    match = re.search(r"\btop\s+(\d{1,3})\b", question)
    if match is None:
        return default
    limit = int(match.group(1))
    if not 1 <= limit <= 10:
        raise AskRoutingError(
            AskRoutingErrorCode.INVALID_PARAMETERS,
            "Ranked questions support a limit from 1 to 10.",
        )
    return limit


def parse_ask_intent(question: str) -> AskRoute:
    """Route a narrowly supported analytics question without an LLM or arbitrary query language."""

    normalized = _normalize_question(question)
    status_values = [
        status
        for status in ("pending", "paid", "processing", "completed", "cancelled", "refunded")
        if re.search(rf"\b{status}\b", normalized)
    ]
    if len(status_values) > 1:
        raise AskRoutingError(
            AskRoutingErrorCode.AMBIGUOUS,
            "Ask about one sales status at a time.",
        )

    matches: list[AskIntent] = []
    if re.search(r"\b(?:sales?|orders?)\s+status\b", normalized) or (
        status_values and re.search(r"\b(?:sales?|orders?)\b", normalized)
    ):
        matches.append(AskIntent.SALES_STATUS)
    if re.search(r"\bproducts?\b", normalized) and re.search(
        r"\b(?:top|best|leading|highest|most\s+revenue|sold\s+the\s+most|best[- ]selling)\b",
        normalized,
    ):
        matches.append(AskIntent.TOP_PRODUCT)
    if re.search(r"\brevenue\b", normalized) and re.search(
        r"\b(?:decline|declined|decrease|decreased|drop|dropped|fall|fell|down)\b",
        normalized,
    ):
        matches.append(AskIntent.REVENUE_DECLINE)
    if re.search(r"\bcustomers?\b", normalized) and re.search(
        r"\b(?:top|best|leading|highest|most\s+valuable)\b",
        normalized,
    ):
        matches.append(AskIntent.TOP_CUSTOMERS)
    if (
        re.search(r"\b(?:summary|overview)\b", normalized)
        and re.search(r"\b(?:business|company|performance)\b", normalized)
    ) or re.search(r"\bhow\s+is\s+(?:the\s+)?business\s+doing\b", normalized):
        matches.append(AskIntent.BUSINESS_SUMMARY)

    unique_matches = list(dict.fromkeys(matches))
    if not unique_matches:
        raise AskRoutingError(
            AskRoutingErrorCode.UNSUPPORTED,
            "This analytics question is not supported.",
        )
    if len(unique_matches) > 1:
        raise AskRoutingError(
            AskRoutingErrorCode.AMBIGUOUS,
            "Ask one supported analytics question at a time.",
        )

    intent = unique_matches[0]
    if intent is AskIntent.SALES_STATUS:
        parameters: AskParameters = SalesStatusParameters(
            status=cast(
                Literal[
                    "pending",
                    "paid",
                    "processing",
                    "completed",
                    "cancelled",
                    "refunded",
                ]
                | None,
                status_values[0] if status_values else None,
            )
        )
    elif intent is AskIntent.TOP_PRODUCT:
        parameters = TopProductParameters(limit=_requested_limit(normalized, 1))
    elif intent is AskIntent.REVENUE_DECLINE:
        parameters = RevenueDeclineParameters()
    elif intent is AskIntent.TOP_CUSTOMERS:
        parameters = TopCustomersParameters(limit=_requested_limit(normalized, 5))
    else:
        parameters = BusinessSummaryParameters()
    return AskRoute(intent=intent, parameters=parameters)
