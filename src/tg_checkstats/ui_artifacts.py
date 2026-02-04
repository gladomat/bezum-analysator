"""UI artifact generation for tg-checkstats.

This module writes a chart-ready, UI-focused data contract under
`<run_dir>/derived/ui/` so the frontend/server does not need to parse `events.csv`
or recompute calendar features.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

from tg_checkstats.io import write_csv


def write_ui_artifacts(
    out_dir: Path,
    *,
    dataset_start: date,
    dataset_end: date,
    daily_rows: List[Mapping[str, object]],
    month_rows: List[Mapping[str, object]],
    day_hour_counts: Dict[Tuple[date, int], Tuple[int, int]],
) -> None:
    """Write all required UI artifacts under `<run_dir>/derived/ui/`.

    Args:
        out_dir: The run directory.
        dataset_start: First timezone-local date in the dataset.
        dataset_end: Last timezone-local date in the dataset.
        daily_rows: Dense daily totals as written to `derived/daily_counts.csv`.
        month_rows: Month totals and normalized rates as written to `derived/month_counts_normalized.csv`.
        day_hour_counts: Sparse `(date, hour)` -> `(check_message_count, check_event_count)` counts.
    """
    ui_dir = out_dir / "derived" / "ui"

    calendar_rows = build_calendar_day_index_rows(dataset_start, dataset_end)
    write_csv(
        ui_dir / "calendar_day_index.csv",
        calendar_rows,
        [
            "date",
            "month",
            "weekday_idx",
            "weekday",
            "iso_year",
            "iso_week",
            "week_start_date",
            "week_of_month",
        ],
    )

    day_rows = build_day_counts_rows(daily_rows, calendar_rows)
    write_csv(
        ui_dir / "day_counts.csv",
        day_rows,
        [
            "date",
            "check_message_count",
            "check_event_count",
            "month",
            "weekday_idx",
            "weekday",
            "iso_year",
            "iso_week",
            "week_start_date",
            "week_of_month",
        ],
    )

    month_counts_rows = build_month_counts_rows(month_rows)
    write_csv(
        ui_dir / "month_counts.csv",
        month_counts_rows,
        [
            "month",
            "month_check_message_count",
            "month_check_event_count",
            "days_in_range",
            "messages_per_day_in_range",
            "events_per_day_in_range",
        ],
    )

    day_hour_rows = build_day_hour_counts_rows(day_hour_counts)
    write_csv(
        ui_dir / "day_hour_counts.csv",
        day_hour_rows,
        ["date", "hour", "check_message_count", "check_event_count"],
    )

    month_weekday_rows = build_month_weekday_stats_rows(day_rows)
    write_csv(
        ui_dir / "month_weekday_stats.csv",
        month_weekday_rows,
        [
            "month",
            "weekday_idx",
            "weekday",
            "weekday_occurrences_in_range",
            "check_message_count",
            "check_event_count",
            "mean_messages_per_weekday_in_range",
            "mean_events_per_weekday_in_range",
        ],
    )


def weekday_label(idx: int) -> str:
    """Return weekday label for 0=Mon..6=Sun."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]


def build_calendar_day_index_rows(start_date: date, end_date: date) -> List[dict]:
    """Build dense calendar feature rows for each date in the dataset range."""
    rows: List[dict] = []
    current = start_date
    while current <= end_date:
        weekday_idx = current.weekday()
        iso_year, iso_week, _ = current.isocalendar()
        week_start = current - timedelta(days=weekday_idx)
        rows.append(
            {
                "date": current.isoformat(),
                "month": f"{current.year:04d}-{current.month:02d}",
                "weekday_idx": weekday_idx,
                "weekday": weekday_label(weekday_idx),
                "iso_year": iso_year,
                "iso_week": iso_week,
                "week_start_date": week_start.isoformat(),
                "week_of_month": 0,  # filled below
            }
        )
        current += timedelta(days=1)

    weeks_by_month: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        weeks_by_month[row["month"]].append(row["week_start_date"])

    week_ordinals: Dict[Tuple[str, str], int] = {}
    for month, starts in weeks_by_month.items():
        unique = sorted(set(starts))
        for idx, week_start_date in enumerate(unique, start=1):
            week_ordinals[(month, week_start_date)] = idx

    for row in rows:
        row["week_of_month"] = week_ordinals[(row["month"], row["week_start_date"])]
    return rows


def build_day_counts_rows(
    daily_rows: List[Mapping[str, object]],
    calendar_rows: List[Mapping[str, object]],
) -> List[dict]:
    """Join dense daily totals with calendar features for the UI contract."""
    calendar_by_date: Dict[str, Mapping[str, object]] = {
        str(row["date"]): row for row in calendar_rows
    }

    rows: List[dict] = []
    for daily in daily_rows:
        date_value = str(daily.get("date_berlin") or daily.get("date"))
        cal = calendar_by_date.get(date_value)
        if cal is None:
            raise ValueError(f"calendar index missing date={date_value}")
        rows.append(
            {
                "date": date_value,
                "check_message_count": int(daily["check_message_count"]),
                "check_event_count": int(daily["check_event_count"]),
                "month": cal["month"],
                "weekday_idx": int(cal["weekday_idx"]),
                "weekday": cal["weekday"],
                "iso_year": int(cal["iso_year"]),
                "iso_week": int(cal["iso_week"]),
                "week_start_date": cal["week_start_date"],
                "week_of_month": int(cal["week_of_month"]),
            }
        )
    return rows


def build_month_counts_rows(month_rows: List[Mapping[str, object]]) -> List[dict]:
    """Transform analyzer month rollups into the UI `month_counts.csv` schema."""
    rows: List[dict] = []
    for row in month_rows:
        rows.append(
            {
                "month": row["month"],
                "month_check_message_count": int(row["month_message_count"]),
                "month_check_event_count": int(row["month_event_count"]),
                "days_in_range": int(row["days_in_month_in_range"]),
                "messages_per_day_in_range": float(row["messages_per_day_in_month"]),
                "events_per_day_in_range": float(row["events_per_day_in_month"]),
            }
        )
    return rows


def build_day_hour_counts_rows(
    day_hour_counts: Dict[Tuple[date, int], Tuple[int, int]]
) -> List[dict]:
    """Build sparse `(date, hour)` rows for week drilldowns."""
    rows: List[dict] = []
    for (day, hour), (message_count, event_count) in sorted(day_hour_counts.items()):
        if message_count == 0 and event_count == 0:
            continue
        rows.append(
            {
                "date": day.isoformat(),
                "hour": hour,
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def build_month_weekday_stats_rows(day_rows: List[Mapping[str, object]]) -> List[dict]:
    """Build month×weekday totals and means from dense day totals."""
    totals: Dict[Tuple[str, int], Tuple[int, int, int]] = {}
    # (month, weekday_idx) -> (occurrences, message_total, event_total)
    for row in day_rows:
        month = str(row["month"])
        weekday_idx = int(row["weekday_idx"])
        key = (month, weekday_idx)
        occ, msg_total, evt_total = totals.get(key, (0, 0, 0))
        totals[key] = (
            occ + 1,
            msg_total + int(row["check_message_count"]),
            evt_total + int(row["check_event_count"]),
        )

    out: List[dict] = []
    for (month, weekday_idx), (occ, msg_total, evt_total) in sorted(totals.items()):
        out.append(
            {
                "month": month,
                "weekday_idx": weekday_idx,
                "weekday": weekday_label(weekday_idx),
                "weekday_occurrences_in_range": occ,
                "check_message_count": msg_total,
                "check_event_count": evt_total,
                "mean_messages_per_weekday_in_range": round(msg_total / occ, 6) if occ else 0.0,
                "mean_events_per_weekday_in_range": round(evt_total / occ, 6) if occ else 0.0,
            }
        )

    return out
