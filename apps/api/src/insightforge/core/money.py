from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MINOR_UNIT = Decimal("0.01")
MAX_MONEY_MINOR = 99_999_999_999_999


def minor_to_decimal(value_minor: int) -> Decimal:
    """Convert an API minor-unit integer to an exact two-decimal amount."""

    if abs(value_minor) > MAX_MONEY_MINOR:
        raise ValueError("Money amount exceeds the supported range.")
    return (Decimal(value_minor) / 100).quantize(MINOR_UNIT)


def decimal_to_minor(value: Decimal) -> int:
    """Convert a persisted decimal amount to an exact minor-unit integer."""

    rounded = value.quantize(MINOR_UNIT, rounding=ROUND_HALF_UP)
    return int(rounded * 100)
