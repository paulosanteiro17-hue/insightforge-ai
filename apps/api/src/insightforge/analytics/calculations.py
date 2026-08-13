from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

ChangeStatus = Literal["increase", "decrease", "unchanged", "new", "not_comparable"]


def comparison(
    current: int | float | None,
    previous: int | float | None,
) -> tuple[float | None, ChangeStatus]:
    if current is None or previous is None:
        return None, "not_comparable"
    if previous == 0:
        if current == 0:
            return None, "unchanged"
        if current > 0:
            return None, "new"
        return None, "not_comparable"
    ratio = (current - previous) / previous
    if ratio > 0:
        return ratio, "increase"
    if ratio < 0:
        return ratio, "decrease"
    return 0.0, "unchanged"


def bucket_dates(start: date, end: date, granularity: str) -> list[date]:
    if granularity == "day":
        cursor = start
        step = timedelta(days=1)
    elif granularity == "week":
        cursor = start - timedelta(days=start.weekday())
        step = timedelta(days=7)
    else:
        cursor = start.replace(day=1)
        result: list[date] = []
        while cursor < end:
            result.append(cursor)
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)
        return result
    result = []
    while cursor < end:
        result.append(cursor)
        cursor += step
    return result
