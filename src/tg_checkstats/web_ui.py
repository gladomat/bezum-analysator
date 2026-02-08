"""Read and shape tg-checkstats UI artifacts into chart-ready JSON payloads."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

from tg_checkstats.bayes import BetaPosteriorSummary, beta_posterior_summary
from tg_checkstats.line_universe import BUS_LINES, REGIONALBUS_LINES, TRAM_LINES


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
        self.month_posteriors, self.month_weekday_posteriors = self._compute_posteriors()
        self.month_weekday_time_windows = self._compute_month_weekday_time_windows()
        self.month_top_lines_by_mode = self._compute_month_top_lines_by_mode()
        self.top_lines_by_mode = self._compute_top_lines_by_mode()

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
        out: list[dict] = []
        for row in self.months:
            month = row.get("month")
            posterior = self.month_posteriors.get(month)
            out.append({**row, **_posterior_payload(posterior)})
        return out

    def get_top_lines(self, *, limit: int | None = None) -> dict[str, list[dict]]:
        """Return top checked lines split by transport mode.

        Args:
            limit: Maximum number of rows per mode bucket; `None` means all.

        Returns:
            Dict with `tram` and `bus` keys; each contains sorted rows with
            `line_id` and `check_event_count`.
        """
        n = None if limit is None else max(1, int(limit))
        return {
            "tram": self.top_lines_by_mode.get("tram", [])[:n] if n is not None else self.top_lines_by_mode.get("tram", []),
            "bus": self.top_lines_by_mode.get("bus", [])[:n] if n is not None else self.top_lines_by_mode.get("bus", []),
        }

    def get_predict_line(
        self,
        *,
        line_id: str,
        mode: str,
        weekday_idx: int,
        prior_alpha: float = 0.5,
        prior_beta: float = 0.5,
    ) -> dict:
        """Return hourly check probabilities for a line on a given weekday.

        This models each (date, hour) bucket as a Bernoulli trial:
          success = 1 if there is >=1 detected check event for that line in that bucket

        Args:
            line_id: Line identifier (e.g., "10").
            mode: "tram" or "bus".
            weekday_idx: 0=Mon..6=Sun (Berlin-local weekday).
            prior_alpha: Beta prior alpha.
            prior_beta: Beta prior beta.

        Returns:
            A dict with 24 hourly rows containing posterior mean + 95% CI.
        """
        normalized_mode = str(mode or "").strip().lower()
        if normalized_mode not in {"tram", "bus"}:
            raise ValueError("mode must be 'tram' or 'bus'")

        w = int(weekday_idx)
        if w < 0 or w > 6:
            raise ValueError("weekday_idx must be in [0,6]")

        normalized_line = str(line_id or "").strip().upper()
        if not normalized_line:
            raise ValueError("line_id required")

        if not _line_in_mode_universe(normalized_line, normalized_mode):
            raise ValueError("line_id not valid for mode")

        weekday_dates = [d for d, row in self.days_by_date.items() if int(row.get("weekday_idx") or 0) == w]
        weekday_set = set(weekday_dates)
        trials = len(weekday_dates)

        successes_by_hour: list[set[str]] = [set() for _ in range(24)]
        events_path = self.run_dir / "derived" / "events.csv"
        if events_path.exists() and trials > 0:
            for row in _read_csv(events_path):
                if str(row.get("mode_guess") or "").strip().lower() != normalized_mode:
                    continue
                if str(row.get("line_id") or "").strip().upper() != normalized_line:
                    continue
                day = str(row.get("date_berlin") or "").strip()
                if day not in weekday_set:
                    continue
                hour = _parse_int(row.get("hour"))
                if 0 <= hour <= 23:
                    successes_by_hour[hour].add(day)

        hours: list[dict] = []
        for hour in range(24):
            successes = len(successes_by_hour[hour])
            if trials <= 0:
                hours.append(
                    {
                        "hour": hour,
                        "trials": 0,
                        "successes": 0,
                        "prob_mean": None,
                        "prob_low": None,
                        "prob_high": None,
                    }
                )
                continue

            posterior = beta_posterior_summary(
                trials=trials,
                successes=successes,
                prior_alpha=prior_alpha,
                prior_beta=prior_beta,
            )
            hours.append(
                {
                    "hour": hour,
                    "trials": trials,
                    "successes": successes,
                    "prob_mean": posterior.mean,
                    "prob_low": posterior.ci_low,
                    "prob_high": posterior.ci_high,
                }
            )

        return {
            "line_id": normalized_line,
            "mode": normalized_mode,
            "weekday_idx": w,
            "weekday": _weekday_label(w),
            "hours": hours,
        }

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
            return {
                "month": month,
                "weeks": [],
                "grid": [],
                "weekday_stats": [],
                "top_lines": {
                    "tram": self.month_top_lines_by_mode.get(month, {}).get("tram", []),
                    "bus": self.month_top_lines_by_mode.get(month, {}).get("bus", []),
                },
            }

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

        weekday_stats = []
        for stat in self.month_weekday_stats.get(month, []):
            key = (month, int(stat.get("weekday_idx", 0)))
            posterior = self.month_weekday_posteriors.get(key)
            window = self.month_weekday_time_windows.get(key)
            weekday_stats.append({**stat, **_posterior_payload(posterior), **_time_window_payload(window)})
        return {
            "month": month,
            "weeks": weeks,
            "grid": grid,
            "weekday_stats": weekday_stats,
            "top_lines": {
                "tram": self.month_top_lines_by_mode.get(month, {}).get("tram", []),
                "bus": self.month_top_lines_by_mode.get(month, {}).get("bus", []),
            },
        }

    def _compute_posteriors(
        self,
        *,
        prior_alpha: float = 0.5,
        prior_beta: float = 0.5,
    ) -> tuple[dict[str, BetaPosteriorSummary], dict[tuple[str, int], BetaPosteriorSummary]]:
        """Compute month-level and month×weekday posteriors from day totals.

        We model each day as a Bernoulli trial:
          success = 1 if check_event_count > 0 else 0

        This uses a conjugate Beta prior (Jeffreys by default), so the posterior
        is analytic and fast.
        """
        month_trials: dict[str, int] = {}
        month_successes: dict[str, int] = {}
        month_weekday_trials: dict[tuple[str, int], int] = {}
        month_weekday_successes: dict[tuple[str, int], int] = {}

        for row in self.days_by_date.values():
            month = str(row.get("month") or "")
            if not month:
                continue
            weekday_idx = int(row.get("weekday_idx") or 0)
            success = int(row.get("check_event_count") or 0) > 0

            month_trials[month] = month_trials.get(month, 0) + 1
            month_successes[month] = month_successes.get(month, 0) + (1 if success else 0)

            key = (month, weekday_idx)
            month_weekday_trials[key] = month_weekday_trials.get(key, 0) + 1
            month_weekday_successes[key] = month_weekday_successes.get(key, 0) + (1 if success else 0)

        month_posteriors: dict[str, BetaPosteriorSummary] = {}
        for month, trials in month_trials.items():
            month_posteriors[month] = beta_posterior_summary(
                trials=trials,
                successes=month_successes.get(month, 0),
                prior_alpha=prior_alpha,
                prior_beta=prior_beta,
            )

        month_weekday_posteriors: dict[tuple[str, int], BetaPosteriorSummary] = {}
        for key, trials in month_weekday_trials.items():
            month_weekday_posteriors[key] = beta_posterior_summary(
                trials=trials,
                successes=month_weekday_successes.get(key, 0),
                prior_alpha=prior_alpha,
                prior_beta=prior_beta,
            )

        return month_posteriors, month_weekday_posteriors

    def _compute_month_weekday_time_windows(self) -> dict[tuple[str, int], dict]:
        """Compute per-(month,weekday) hourly "probable check window" summaries.

        This uses the hourly event counts derived by the analyzer (`derived/ui/day_hour_counts.csv`).
        For each (month, weekday_idx), we build a weighted hour distribution with weights:
          w_h = sum(check_event_count for that hour across all matching days)

        We then compute:
        - p10 and p90 hours (discrete, hour bins)
        - weighted mean hour
        - weighted SD in minutes
        """
        hour_weights: dict[tuple[str, int], list[int]] = {}
        for day_str, row in self.days_by_date.items():
            month = str(row.get("month") or "")
            if not month:
                continue
            weekday_idx = int(row.get("weekday_idx") or 0)
            key = (month, weekday_idx)
            weights = hour_weights.setdefault(key, [0] * 24)
            sparse = self.day_hours_by_date.get(day_str, {})
            for hour in range(24):
                _, evt = sparse.get(hour, (0, 0))
                weights[hour] += int(evt)

        out: dict[tuple[str, int], dict] = {}
        for key, weights in hour_weights.items():
            out[key] = _weighted_hour_window(weights, q_low=0.10, q_high=0.90)
        return out

    def _compute_top_lines_by_mode(self) -> dict[str, list[dict]]:
        """Load top lines by mode from pre-computed CSV or fallback to events.csv."""
        # Prefer pre-computed top_lines.csv (written by ui_artifacts)
        top_lines_path = self.ui_dir / "top_lines.csv"
        if top_lines_path.exists():
            rows = _read_csv(top_lines_path)
            out: dict[str, list[dict]] = {"tram": [], "bus": []}
            for row in rows:
                mode = str(row.get("mode") or "").strip().lower()
                if mode not in {"tram", "bus"}:
                    continue
                out[mode].append({
                    "line_id": str(row.get("line_id") or "").strip().upper(),
                    "check_event_count": _parse_int(row.get("check_event_count")),
                })
            return out

        # Fallback: compute from events.csv for backwards compatibility
        events_path = self.run_dir / "derived" / "events.csv"
        by_mode_line: dict[tuple[str, str], int] = {}
        if events_path.exists():
            rows = _read_csv(events_path)
            for row in rows:
                mode = str(row.get("mode_guess") or "").strip().lower()
                line_id = str(row.get("line_id") or "").strip().upper()
                if not line_id or mode not in {"tram", "bus"}:
                    continue
                weight = _parse_int(row.get("event_weight"))
                by_mode_line[(mode, line_id)] = by_mode_line.get((mode, line_id), 0) + max(1, weight)

        tram_universe = sorted(TRAM_LINES, key=_line_sort_key)
        bus_universe = sorted(BUS_LINES | REGIONALBUS_LINES, key=_line_sort_key)

        out: dict[str, list[dict]] = {"tram": [], "bus": []}
        for mode, universe in (("tram", tram_universe), ("bus", bus_universe)):
            mode_rows = [
                {
                    "line_id": line_id,
                    "check_event_count": int(by_mode_line.get((mode, line_id), 0)),
                }
                for line_id in universe
            ]
            mode_rows.sort(key=lambda r: (-int(r["check_event_count"]), _line_sort_key(str(r["line_id"]))))
            out[mode] = mode_rows
        return out

    def _compute_month_top_lines_by_mode(self) -> dict[str, dict[str, list[dict]]]:
        """Aggregate top lines per month with zero-filled tram/bus universes."""
        events_path = self.run_dir / "derived" / "events.csv"
        by_month_mode_line: dict[tuple[str, str, str], int] = {}
        if events_path.exists():
            rows = _read_csv(events_path)
            for row in rows:
                month = str(row.get("month") or "").strip()
                mode = str(row.get("mode_guess") or "").strip().lower()
                line_id = str(row.get("line_id") or "").strip().upper()
                if not month or not line_id or mode not in {"tram", "bus"}:
                    continue
                weight = _parse_int(row.get("event_weight"))
                key = (month, mode, line_id)
                by_month_mode_line[key] = by_month_mode_line.get(key, 0) + max(1, weight)

        tram_universe = sorted(TRAM_LINES, key=_line_sort_key)
        bus_universe = sorted(BUS_LINES | REGIONALBUS_LINES, key=_line_sort_key)
        months = sorted({str(row.get("month") or "").strip() for row in self.months if str(row.get("month") or "").strip()})

        out: dict[str, dict[str, list[dict]]] = {}
        for month in months:
            month_rows: dict[str, list[dict]] = {}
            for mode, universe in (("tram", tram_universe), ("bus", bus_universe)):
                rows_for_mode = [
                    {
                        "line_id": line_id,
                        "check_event_count": int(by_month_mode_line.get((month, mode, line_id), 0)),
                    }
                    for line_id in universe
                ]
                rows_for_mode.sort(key=lambda r: (-int(r["check_event_count"]), _line_sort_key(str(r["line_id"]))))
                month_rows[mode] = rows_for_mode
            out[month] = month_rows
        return out


def _line_sort_key(line_id: str) -> tuple[int, str]:
    """Return a stable sort key for numeric-first line IDs."""
    value = str(line_id).strip().upper()
    if value.isdigit():
        return (0, f"{int(value):04d}")
    return (1, value)


def _line_in_mode_universe(line_id: str, mode: str) -> bool:
    """Return True if line_id is a known line for the requested mode."""
    value = str(line_id).strip().upper()
    base = value[:-1] if value != "E" and value.endswith("E") else value
    if mode == "tram":
        return base in TRAM_LINES
    if mode == "bus":
        return base in (BUS_LINES | REGIONALBUS_LINES)
    return False


def _posterior_payload(posterior: BetaPosteriorSummary | None) -> dict:
    """Serialize posterior summary into JSON-friendly fields."""
    if posterior is None:
        return {
            "posterior_check_prob_mean": None,
            "posterior_check_prob_low": None,
            "posterior_check_prob_high": None,
            "posterior_trials": 0,
            "posterior_successes": 0,
        }
    return {
        "posterior_check_prob_mean": posterior.mean,
        "posterior_check_prob_low": posterior.ci_low,
        "posterior_check_prob_high": posterior.ci_high,
        "posterior_trials": posterior.trials,
        "posterior_successes": posterior.successes,
    }


def _time_window_payload(window: dict | None) -> dict:
    """Serialize a time window summary into JSON-friendly fields."""
    if not window:
        return {
            "probable_check_total_events": 0,
            "probable_check_start_hour_p10": None,
            "probable_check_end_hour_p90": None,
            "probable_check_mean_hour": None,
            "probable_check_sd_minutes": None,
        }
    return dict(window)


def _weighted_hour_window(weights: list[int], *, q_low: float, q_high: float) -> dict:
    """Compute discrete weighted quantiles + mean + SD for hour-of-day bins.

    Args:
        weights: Length-24 list where index=hour and value=weight (>=0).
        q_low: Lower quantile in [0,1].
        q_high: Upper quantile in [0,1].

    Returns:
        Dict containing `probable_check_*` fields.
    """
    if len(weights) != 24:
        raise ValueError("weights must have length 24")
    total = sum(int(w) for w in weights)
    if total <= 0:
        return {
            "probable_check_total_events": 0,
            "probable_check_start_hour_p10": None,
            "probable_check_end_hour_p90": None,
            "probable_check_mean_hour": None,
            "probable_check_sd_minutes": None,
        }

    def quantile(q: float) -> int:
        threshold = q * total
        cum = 0
        for hour, w in enumerate(weights):
            cum += int(w)
            if cum >= threshold:
                return hour
        return 23

    start_hour = quantile(q_low)
    end_hour = quantile(q_high)

    mean_hour = sum(hour * int(w) for hour, w in enumerate(weights)) / total
    mean_sq = sum((hour * hour) * int(w) for hour, w in enumerate(weights)) / total
    var = max(0.0, mean_sq - mean_hour * mean_hour)
    sd_hours = var ** 0.5
    sd_minutes = sd_hours * 60.0

    return {
        "probable_check_total_events": int(total),
        "probable_check_start_hour_p10": int(start_hour),
        "probable_check_end_hour_p90": int(end_hour),
        "probable_check_mean_hour": float(mean_hour),
        "probable_check_sd_minutes": float(sd_minutes),
    }
