"""Aggregation helpers for tg-checkstats."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, List, Tuple


def iter_dates(start: date, end: date) -> Iterable[date]:
    """Yield dates from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_weekday_hour_matrix(
    counts: Dict[Tuple[int, int], Tuple[int, float]]
) -> List[dict]:
    """Build a zero-filled weekday×hour matrix.

    counts maps (weekday_idx, hour) -> (message_count, event_count).
    """
    rows = []
    for weekday_idx in range(7):
        for hour in range(24):
            message_count, event_count = counts.get((weekday_idx, hour), (0, 0))
            rows.append(
                {
                    "weekday_idx": weekday_idx,
                    "weekday": _weekday_label(weekday_idx),
                    "hour": hour,
                    "check_message_count": message_count,
                    "check_event_count": event_count,
                }
            )
    return rows


def build_iso_week_series(
    start_date: date,
    end_date: date,
    counts: Dict[Tuple[int, int], Tuple[int, float]],
) -> List[dict]:
    """Build a zero-filled ISO week series over a date range."""
    days_by_week: Dict[Tuple[int, int], int] = {}
    for day in iter_dates(start_date, end_date):
        iso_year, iso_week, _ = day.isocalendar()
        key = (iso_year, iso_week)
        days_by_week[key] = days_by_week.get(key, 0) + 1

    rows = []
    for (iso_year, iso_week), days_in_range in sorted(days_by_week.items()):
        message_count, event_count = counts.get((iso_year, iso_week), (0, 0))
        week_start = date.fromisocalendar(iso_year, iso_week, 1)
        rows.append(
            {
                "iso_year": iso_year,
                "iso_week": iso_week,
                "iso_week_start_date_berlin": week_start.isoformat(),
                "days_in_week_in_range": days_in_range,
                "is_partial_week": days_in_range < 7,
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def _weekday_label(idx: int) -> str:
    """Return the weekday label for a 0=Mon..6=Sun index."""
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return labels[idx]
