"""Read and shape tg-checkstats UI artifacts into chart-ready JSON payloads."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Mapping, Tuple


def _weekday_label(idx: int) -> str:
    """Return weekday label for 0=Mon..6=Sun."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of dicts (string values)."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_int(value: str | None) -> int:
    """Parse an integer from a CSV field."""
    if value is None or value == "":
        return 0
    return int(value)


@dataclass(frozen=True)
class DatasetRange:
    """Dataset date range in timezone-local dates."""

    start: date
    end: date


class UiArtifacts:
    """Load `<run_dir>/derived/ui/*` artifacts and expose API-shaped payloads."""

    def __init__(self, run_dir: Path):
        """Create a reader for a specific run directory."""
        self.run_dir = run_dir
        self.ui_dir = run_dir / "derived" / "ui"
        self.metadata = self._read_metadata()
        self.dataset_range = self._read_dataset_range()

        self.months = self._load_month_counts()
        self.days_by_date = self._load_day_counts()
        self.day_hours_by_date = self._load_day_hour_counts()
        self.month_weekday_stats = self._load_month_weekday_stats()

    def _read_metadata(self) -> Mapping[str, object]:
        """Read run metadata JSON."""
        path = self.run_dir / "run_metadata.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _read_dataset_range(self) -> DatasetRange:
        """Extract dataset start/end dates from metadata."""
        dataset = self.metadata.get("dataset") if isinstance(self.metadata, dict) else None
        if not isinstance(dataset, dict):
            raise ValueError("run_metadata.json missing dataset")
        start_str = dataset.get("start_berlin_date") or dataset.get("start_date")
        end_str = dataset.get("end_berlin_date") or dataset.get("end_date")
        if not isinstance(start_str, str) or not isinstance(end_str, str):
            raise ValueError("run_metadata.json missing dataset start/end dates")
        return DatasetRange(start=date.fromisoformat(start_str), end=date.fromisoformat(end_str))

    def _load_month_counts(self) -> list[dict]:
        """Load month overview rows."""
        rows = _read_csv(self.ui_dir / "month_counts.csv")
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "month": row["month"],
                    "month_check_message_count": _parse_int(row.get("month_check_message_count")),
                    "month_check_event_count": _parse_int(row.get("month_check_event_count")),
                    "days_in_range": _parse_int(row.get("days_in_range")),
                    "messages_per_day_in_range": float(row.get("messages_per_day_in_range") or 0.0),
                    "events_per_day_in_range": float(row.get("events_per_day_in_range") or 0.0),
                }
            )
        return out

    def _load_day_counts(self) -> dict[str, dict]:
        """Load dense day rows keyed by date."""
        rows = _read_csv(self.ui_dir / "day_counts.csv")
        out: dict[str, dict] = {}
        for row in rows:
            out[row["date"]] = {
                "date": row["date"],
                "month": row["month"],
                "weekday_idx": _parse_int(row.get("weekday_idx")),
                "weekday": row.get("weekday") or _weekday_label(_parse_int(row.get("weekday_idx"))),
                "iso_year": _parse_int(row.get("iso_year")),
                "iso_week": _parse_int(row.get("iso_week")),
                "week_start_date": row.get("week_start_date") or "",
                "week_of_month": _parse_int(row.get("week_of_month")),
                "check_message_count": _parse_int(row.get("check_message_count")),
                "check_event_count": _parse_int(row.get("check_event_count")),
            }
        return out

    def _load_day_hour_counts(self) -> dict[str, dict[int, tuple[int, int]]]:
        """Load sparse day-hour rows as date -> hour -> (msg, evt)."""
        rows = _read_csv(self.ui_dir / "day_hour_counts.csv")
        out: dict[str, dict[int, tuple[int, int]]] = {}
        for row in rows:
            date_str = row["date"]
            hour = _parse_int(row.get("hour"))
            msg = _parse_int(row.get("check_message_count"))
            evt = _parse_int(row.get("check_event_count"))
            out.setdefault(date_str, {})[hour] = (msg, evt)
        return out

    def _load_month_weekday_stats(self) -> dict[str, list[dict]]:
        """Load month weekday mean stats."""
        rows = _read_csv(self.ui_dir / "month_weekday_stats.csv")
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            month = row["month"]
            grouped.setdefault(month, []).append(
                {
                    "month": month,
                    "weekday_idx": _parse_int(row.get("weekday_idx")),
                    "weekday": row.get("weekday") or _weekday_label(_parse_int(row.get("weekday_idx"))),
                    "weekday_occurrences_in_range": _parse_int(row.get("weekday_occurrences_in_range")),
                    "check_message_count": _parse_int(row.get("check_message_count")),
                    "check_event_count": _parse_int(row.get("check_event_count")),
                    "mean_messages_per_weekday_in_range": float(
                        row.get("mean_messages_per_weekday_in_range") or 0.0
                    ),
                    "mean_events_per_weekday_in_range": float(
                        row.get("mean_events_per_weekday_in_range") or 0.0
                    ),
                }
            )
        for month, items in grouped.items():
            grouped[month] = sorted(items, key=lambda r: r["weekday_idx"])
        return grouped

    def get_months(self) -> list[dict]:
        """Return overview rows for all months."""
        return list(self.months)

    def get_week(self, week_start_date: str) -> dict:
        """Return week detail payload for a given Monday week start date."""
        start = date.fromisoformat(week_start_date)
        if start.weekday() != 0:
            raise ValueError("week_start_date must be a Monday (YYYY-MM-DD)")

        days: list[dict] = []
        for idx in range(7):
            day = start + timedelta(days=idx)
            day_str = day.isoformat()
            weekday_idx = day.weekday()
            base = {
                "date": day_str,
                "weekday_idx": weekday_idx,
                "weekday": _weekday_label(weekday_idx),
            }
            in_range = self.dataset_range.start <= day <= self.dataset_range.end
            if in_range and day_str in self.days_by_date:
                d = self.days_by_date[day_str]
                base["check_message_count"] = d["check_message_count"]
                base["check_event_count"] = d["check_event_count"]
            else:
                base["check_message_count"] = 0
                base["check_event_count"] = 0

            hours: list[dict] = []
            sparse = self.day_hours_by_date.get(day_str, {})
            for hour in range(24):
                msg, evt = sparse.get(hour, (0, 0))
                hours.append(
                    {
                        "hour": hour,
                        "check_message_count": msg,
                        "check_event_count": evt,
                    }
                )
            base["hours"] = hours
            days.append(base)

        return {"week_start_date": week_start_date, "days": days}

    def get_month(self, month: str) -> dict:
        """Return month detail payload with a week grid and weekday stats."""
        in_month_dates = sorted(
            d for d, row in self.days_by_date.items() if row.get("month") == month
        )
        if not in_month_dates:
            return {"month": month, "weeks": [], "grid": [], "weekday_stats": []}

        first = date.fromisoformat(in_month_dates[0])
        last = date.fromisoformat(in_month_dates[-1])
        start_week = first - timedelta(days=first.weekday())
        end_week = last - timedelta(days=last.weekday())

        weeks: list[str] = []
        grid: list[dict] = []
        current = start_week
        while current <= end_week:
            week_start_str = current.isoformat()
            weeks.append(week_start_str)
            for weekday_idx in range(7):
                day = current + timedelta(days=weekday_idx)
                day_str = day.isoformat()
                in_range = self.dataset_range.start <= day <= self.dataset_range.end
                day_row = self.days_by_date.get(day_str) if in_range else None
                grid.append(
                    {
                        "date": day_str,
                        "week_start_date": week_start_str,
                        "weekday_idx": weekday_idx,
                        "weekday": _weekday_label(weekday_idx),
                        "in_month": day_str in in_month_dates,
                        "in_range": in_range,
                        "check_message_count": int(day_row["check_message_count"]) if day_row else 0,
                        "check_event_count": int(day_row["check_event_count"]) if day_row else 0,
                    }
                )
            current += timedelta(days=7)

        weekday_stats = self.month_weekday_stats.get(month, [])
        return {
            "month": month,
            "weeks": weeks,
            "grid": grid,
            "weekday_stats": weekday_stats,
        }

