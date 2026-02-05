"""Analyze Telegram exports for check events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
from typing import Any, Dict, Iterable, List, Tuple

import ijson
from ijson.common import IncompleteJSONError, JSONError

from tg_checkstats import __version__
from tg_checkstats.aggregate import (
    build_iso_week_series,
    build_weekday_hour_matrix,
    iter_dates,
)
from tg_checkstats.detector import detect_event
from tg_checkstats.io import write_csv, write_json
from tg_checkstats.parse import normalize_text, parse_timestamp
from tg_checkstats.ui_artifacts import write_ui_artifacts

try:  # pragma: no cover - python <3.9 fallback
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

BERLIN_TZ = ZoneInfo("Europe/Berlin")


@dataclass
class AnalyzeConfig:
    """Analysis configuration settings."""

    event_count_policy: str = "message"
    text_trunc_len: int = 500
    include_service: bool = False
    include_bots: bool = True
    include_forwards: bool = True
    stitch_followups: bool = True
    stitch_window_seconds: int = 5 * 60


@dataclass
class _OpenEventForStitching:
    """Tracks the last open event row for a sender to stitch follow-up details."""

    event_row: Dict[str, Any]
    last_timestamp_utc: datetime
    stitched_message_ids: List[int]


def analyze_export(
    input_path: Path,
    out_dir: Path,
    config: AnalyzeConfig | None = None,
    tg_checkstats_argv: List[str] | None = None,
    telegram_download_chat_argv: List[str] | None = None,
    export_retry_count: int | None = None,
    export_retry_delay_seconds: int | None = None,
) -> Dict[str, Any]:
    """Analyze a telegram-download-chat JSON export and write outputs."""
    cfg = config or AnalyzeConfig()

    started_utc = datetime.now(timezone.utc)

    counts: Dict[str, int] = {
        "messages_scanned": 0,
        "messages_included": 0,
        "messages_excluded_service": 0,
        "messages_excluded_no_message_id": 0,
        "messages_excluded_no_timestamp": 0,
        "messages_excluded_invalid_timestamp": 0,
        "messages_excluded_duplicate_id": 0,
        "messages_excluded_bot": 0,
        "messages_excluded_forward": 0,
        "messages_text_non_string": 0,
        "messages_caption_non_string": 0,
        "events_matched_total": 0,
        "events_matched_k_token_only": 0,
        "events_matched_keyword_only": 0,
        "events_matched_both": 0,
        "events_weight_total": 0,
        "events_weight_k_token_only": 0,
        "events_weight_keyword_only": 0,
        "events_weight_both": 0,
        "naive_timestamp_count": 0,
    }

    events: List[Dict[str, Any]] = []
    daily_counts: Dict[date, Tuple[int, int]] = {}
    weekday_counts: Dict[int, Tuple[int, int]] = {}
    hour_counts: Dict[int, Tuple[int, int]] = {}
    weekday_hour_counts: Dict[Tuple[int, int], Tuple[int, int]] = {}
    day_hour_counts: Dict[Tuple[date, int], Tuple[int, int]] = {}
    week_of_month_counts: Dict[int, Tuple[int, int]] = {}
    month_week_of_month_counts: Dict[Tuple[str, int], Tuple[int, int]] = {}
    month_counts: Dict[str, Tuple[int, int]] = {}
    iso_week_counts: Dict[Tuple[int, int], Tuple[int, int]] = {}

    dataset_start: date | None = None
    dataset_end: date | None = None

    seen_ids: set[int] = set()

    open_event_by_sender: Dict[str, _OpenEventForStitching] = {}

    for message in iter_messages(input_path):
        counts["messages_scanned"] += 1

        message_id = extract_message_id(message)
        if message_id is None:
            counts["messages_excluded_no_message_id"] += 1
            continue
        if message_id in seen_ids:
            counts["messages_excluded_duplicate_id"] += 1
            continue
        seen_ids.add(message_id)

        timestamp_value = extract_timestamp_value(message)
        if timestamp_value is None:
            counts["messages_excluded_no_timestamp"] += 1
            continue

        try:
            timestamp_utc, assumed = parse_timestamp(timestamp_value)
        except (TypeError, ValueError):
            counts["messages_excluded_invalid_timestamp"] += 1
            continue

        if assumed:
            counts["naive_timestamp_count"] += 1

        timestamp_berlin = timestamp_utc.astimezone(BERLIN_TZ)
        message_date = timestamp_berlin.date()

        dataset_start = message_date if dataset_start is None else min(dataset_start, message_date)
        dataset_end = message_date if dataset_end is None else max(dataset_end, message_date)

        if not cfg.include_service and is_service_message(message):
            counts["messages_excluded_service"] += 1
            continue
        if not cfg.include_bots and is_bot_message(message):
            counts["messages_excluded_bot"] += 1
            continue
        if not cfg.include_forwards and is_forward_message(message):
            counts["messages_excluded_forward"] += 1
            continue

        counts["messages_included"] += 1

        sender_key = extract_sender_key(message)

        raw_text = message.get("text") if isinstance(message, dict) else None
        raw_caption = message.get("caption") if isinstance(message, dict) else None

        normalized_text, normalized_caption = normalize_message_text(
            raw_text, raw_caption, counts
        )
        search_text = build_search_text(normalized_text, normalized_caption)

        event_info = detect_event(search_text)
        if not event_info.get("is_check_event", False):
            if (
                cfg.stitch_followups
                and sender_key is not None
                and event_info.get("is_detail_only", False)
                and sender_key in open_event_by_sender
            ):
                stitch = open_event_by_sender[sender_key]
                if (timestamp_utc - stitch.last_timestamp_utc).total_seconds() <= cfg.stitch_window_seconds:
                    _stitch_followup_into_event(stitch, message_id, timestamp_utc, event_info)
                else:
                    # Window expired; drop open stitch state.
                    open_event_by_sender.pop(sender_key, None)
            continue

        event_weight = compute_event_weight(cfg.event_count_policy, event_info["k_token_hit_count"])
        increment_match_counts(counts, event_info, event_weight)

        weekday_idx = timestamp_berlin.weekday()
        weekday_label = weekday_name(weekday_idx)
        iso_year, iso_week, _ = timestamp_berlin.isocalendar()
        month_label = f"{timestamp_berlin.year:04d}-{timestamp_berlin.month:02d}"
        week_of_month = 1 + (timestamp_berlin.day - 1) // 7

        event_row = {
            "event_id": f"evt-{message_id}",
            "message_id": message_id,
            "timestamp_utc": timestamp_utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "timestamp_berlin": timestamp_berlin.isoformat(),
            "date_berlin": message_date.isoformat(),
            "weekday": weekday_label,
            "weekday_idx": weekday_idx,
            "iso_year": iso_year,
            "iso_week": iso_week,
            "month": month_label,
            "time_berlin": timestamp_berlin.strftime("%H:%M:%S"),
            "hour": timestamp_berlin.hour,
            "week_of_month_simple": week_of_month,
            "match_type": event_info["match_type"],
            "event_weight": event_weight,
            "matched_k_values": json.dumps(event_info["matched_k_values"], separators=(",", ":"), ensure_ascii=False),
            "matched_keywords": json.dumps(event_info["matched_keywords"], separators=(",", ":"), ensure_ascii=False),
            "k_token_hit_count": event_info["k_token_hit_count"],
            "confidence_score": event_info.get("confidence_score", 0),
            "k_min": event_info.get("k_min"),
            "k_max": event_info.get("k_max"),
            "k_qualifier": event_info.get("k_qualifier") or "",
            "control_keyword_hit": event_info.get("control_keyword_hit", False),
            "control_keyword_forms": json.dumps(
                event_info.get("control_keyword_forms", []),
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            "line_id": event_info.get("line_id") or "",
            "mode_guess": event_info.get("mode_guess") or "",
            "line_validated": event_info.get("line_validated", False),
            "line_confidence": event_info.get("line_confidence") or "",
            "direction_text": event_info.get("direction_text") or "",
            "direction_polarity": event_info.get("direction_polarity") or "",
            "location_text": event_info.get("location_text") or "",
            "platform_text": event_info.get("platform_text") or "",
            "stitched_message_ids": "[]",
            "text_trunc": search_text[: cfg.text_trunc_len],
            "text_len": len(search_text),
            "text_sha256": sha256_hex(search_text),
        }
        events.append(event_row)

        if cfg.stitch_followups and sender_key is not None:
            open_event_by_sender[sender_key] = _OpenEventForStitching(
                event_row=event_row,
                last_timestamp_utc=timestamp_utc,
                stitched_message_ids=[],
            )

        update_counts(daily_counts, message_date, event_weight)
        update_counts(weekday_counts, weekday_idx, event_weight)
        update_counts(hour_counts, timestamp_berlin.hour, event_weight)
        update_counts(weekday_hour_counts, (weekday_idx, timestamp_berlin.hour), event_weight)
        update_counts(day_hour_counts, (message_date, timestamp_berlin.hour), event_weight)
        update_counts(week_of_month_counts, week_of_month, event_weight)
        update_counts(month_week_of_month_counts, (month_label, week_of_month), event_weight)
        update_counts(month_counts, month_label, event_weight)
        update_counts(iso_week_counts, (iso_year, iso_week), event_weight)

    if dataset_start is None or dataset_end is None:
        dataset_start = date.today()
        dataset_end = date.today()

    derived_dir = out_dir / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    events.sort(key=lambda row: (row["timestamp_utc"], row["message_id"]))
    write_events_csv(derived_dir / "events.csv", events)

    daily_rows = build_daily_rows(dataset_start, dataset_end, daily_counts)
    write_csv(derived_dir / "daily_counts.csv", daily_rows, ["date_berlin", "check_message_count", "check_event_count"])

    weekday_rows = build_weekday_rows(dataset_start, dataset_end, weekday_counts)
    write_csv(
        derived_dir / "weekday_counts.csv",
        weekday_rows,
        [
            "weekday",
            "weekday_idx",
            "check_message_count",
            "check_event_count",
            "weekday_occurrences",
            "mean_messages_per_weekday",
            "mean_events_per_weekday",
        ],
    )

    hour_rows = build_hour_rows(hour_counts)
    write_csv(derived_dir / "hour_counts.csv", hour_rows, ["hour", "check_message_count", "check_event_count"])

    weekday_hour_rows = build_weekday_hour_matrix(weekday_hour_counts)
    write_csv(
        derived_dir / "weekday_hour_counts.csv",
        weekday_hour_rows,
        [
            "weekday",
            "weekday_idx",
            "hour",
            "check_message_count",
            "check_event_count",
        ],
    )

    week_of_month_rows = build_week_of_month_rows(week_of_month_counts)
    write_csv(
        derived_dir / "week_of_month_counts.csv",
        week_of_month_rows,
        ["week_of_month_simple", "check_message_count", "check_event_count"],
    )

    month_week_rows = build_month_week_rows(month_week_of_month_counts)
    write_csv(
        derived_dir / "month_week_of_month_counts.csv",
        month_week_rows,
        ["month", "week_of_month_simple", "check_message_count", "check_event_count"],
    )

    iso_week_rows = build_iso_week_series(dataset_start, dataset_end, iso_week_counts)
    write_csv(
        derived_dir / "iso_week_counts.csv",
        iso_week_rows,
        [
            "iso_year",
            "iso_week",
            "iso_week_start_date_berlin",
            "days_in_week_in_range",
            "is_partial_week",
            "check_message_count",
            "check_event_count",
        ],
    )

    month_rows = build_month_rows(dataset_start, dataset_end, month_counts)
    write_csv(
        derived_dir / "month_counts_normalized.csv",
        month_rows,
        [
            "month",
            "month_message_count",
            "month_event_count",
            "days_in_month_in_range",
            "is_partial_month",
            "messages_per_day_in_month",
            "events_per_day_in_month",
        ],
    )

    write_ui_artifacts(
        out_dir,
        dataset_start=dataset_start,
        dataset_end=dataset_end,
        daily_rows=daily_rows,
        month_rows=month_rows,
        day_hour_counts=day_hour_counts,
    )

    completed_utc = datetime.now(timezone.utc)
    metadata = build_metadata(
        input_path,
        cfg,
        counts,
        dataset_start,
        dataset_end,
        started_utc=started_utc,
        completed_utc=completed_utc,
        tg_checkstats_argv=tg_checkstats_argv,
        telegram_download_chat_argv=telegram_download_chat_argv,
        export_retry_count=export_retry_count,
        export_retry_delay_seconds=export_retry_delay_seconds,
    )
    write_json(out_dir / "run_metadata.json", metadata)

    return metadata


def iter_messages(path: Path) -> Iterable[Dict[str, Any]]:
    """Yield message objects from a JSON export."""
    with path.open("rb") as handle:
        first = first_non_whitespace(handle)

    if first == b"[":
        with path.open("rb") as handle:
            yield from ijson.items(handle, "item")
    else:
        try:
            with path.open("rb") as handle:
                yield from ijson.items(handle, "messages.item")
        except (IncompleteJSONError, JSONError):
            yield from iter_messages_ndjson(path)


def iter_messages_ndjson(path: Path) -> Iterable[Dict[str, Any]]:
    """Yield message objects from an NDJSON (newline-delimited JSON) export."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                yield obj


def first_non_whitespace(handle) -> bytes:
    """Return the first non-whitespace byte from a file handle."""
    while True:
        chunk = handle.read(1)
        if chunk == b"":
            return b""
        if not chunk.isspace():
            return chunk


def extract_message_id(message: Dict[str, Any]) -> int | None:
    """Extract a message ID from known fields."""
    for key in ("id", "message_id", "msg_id"):
        value = message.get(key)
        if isinstance(value, int):
            return value
    return None


def extract_sender_key(message: Dict[str, Any]) -> str | None:
    """Extract a stable-ish sender identifier from known fields.

    This is intentionally best-effort: telegram export formats vary. The key is
    only used to stitch near-term follow-up messages into the previous event.
    """
    for key in ("from_id", "sender_id", "user_id", "author_id"):
        value = message.get(key)
        if isinstance(value, (int, str)):
            return str(value)
        if isinstance(value, dict):
            for subkey in ("user_id", "id", "peer_id", "username"):
                sub = value.get(subkey)
                if isinstance(sub, (int, str)):
                    return str(sub)

    sender = message.get("from")
    if isinstance(sender, str) and sender.strip():
        return sender.strip()
    if isinstance(sender, dict):
        for subkey in ("id", "user_id", "username"):
            sub = sender.get(subkey)
            if isinstance(sub, (int, str)):
                return str(sub)
    return None


def extract_timestamp_value(message: Dict[str, Any]) -> Any:
    """Extract a timestamp value from known fields."""
    for key in ("date", "timestamp", "date_utc", "time", "created_at"):
        if key in message:
            return message.get(key)
    return None


def _stitch_followup_into_event(
    stitch: _OpenEventForStitching,
    message_id: int,
    timestamp_utc: datetime,
    event_info: Dict[str, Any],
) -> None:
    """Merge extracted detail fields from a follow-up message into an open event row."""
    row = stitch.event_row

    def fill_if_missing(key: str, value: Any) -> None:
        current = row.get(key)
        if current in (None, "", "unknown") and value not in (None, "", "unknown"):
            row[key] = value

    fill_if_missing("line_id", event_info.get("line_id") or "")
    fill_if_missing("mode_guess", event_info.get("mode_guess") or "")
    # Preserve existing validation if already true.
    if not row.get("line_validated", False) and event_info.get("line_validated", False):
        row["line_validated"] = True
    fill_if_missing("line_confidence", event_info.get("line_confidence") or "")
    fill_if_missing("direction_text", event_info.get("direction_text") or "")
    fill_if_missing("direction_polarity", event_info.get("direction_polarity") or "")
    fill_if_missing("location_text", event_info.get("location_text") or "")
    fill_if_missing("platform_text", event_info.get("platform_text") or "")

    stitch.stitched_message_ids.append(message_id)
    row["stitched_message_ids"] = json.dumps(stitch.stitched_message_ids, separators=(",", ":"), ensure_ascii=False)
    stitch.last_timestamp_utc = timestamp_utc


def normalize_message_text(
    raw_text: Any,
    raw_caption: Any,
    counts: Dict[str, int],
) -> Tuple[str, str]:
    """Normalize text and caption, tracking non-string counts."""
    text = normalize_text(raw_text)
    if raw_text is not None and not isinstance(raw_text, (str, list)):
        counts["messages_text_non_string"] += 1
    caption = normalize_text(raw_caption)
    if raw_caption is not None and not isinstance(raw_caption, (str, list)):
        counts["messages_caption_non_string"] += 1
    return text, caption


def build_search_text(text: str, caption: str) -> str:
    """Construct search text from normalized text and caption."""
    if text and caption:
        return f"{text}\n{caption}"
    return text or caption or ""


def is_service_message(message: Dict[str, Any]) -> bool:
    """Return True if the message appears to be a service event."""
    return any(key in message for key in ("action", "action_type", "service"))


def is_forward_message(message: Dict[str, Any]) -> bool:
    """Return True if the message appears forwarded."""
    return any(key in message for key in ("forward_from", "fwd_from", "forward_date", "forwarded_from"))


def is_bot_message(message: Dict[str, Any]) -> bool:
    """Return True if the sender appears to be a bot."""
    sender = message.get("from") if isinstance(message, dict) else None
    if isinstance(sender, dict) and sender.get("is_bot") is True:
        return True
    if isinstance(message.get("is_bot"), bool):
        return message.get("is_bot") is True
    return False


def compute_event_weight(policy: str, k_token_hit_count: int) -> int:
    """Compute event weight based on policy."""
    if policy == "token":
        return k_token_hit_count if k_token_hit_count > 0 else 1
    return 1


def increment_match_counts(counts: Dict[str, int], event_info: Dict[str, Any], event_weight: int) -> None:
    """Increment match counters and weights."""
    counts["events_matched_total"] += 1
    counts["events_weight_total"] += event_weight
    match_type = event_info["match_type"]
    if match_type == "k_token":
        counts["events_matched_k_token_only"] += 1
        counts["events_weight_k_token_only"] += event_weight
    elif match_type == "keyword":
        counts["events_matched_keyword_only"] += 1
        counts["events_weight_keyword_only"] += event_weight
    elif match_type == "both":
        counts["events_matched_both"] += 1
        counts["events_weight_both"] += event_weight


def weekday_name(idx: int) -> str:
    """Return weekday label for 0=Mon..6=Sun."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]


def update_counts(
    target: Dict[Any, Tuple[int, int]],
    key: Any,
    event_weight: int,
) -> None:
    """Update message and event counts for a bucket."""
    message_count, event_count = target.get(key, (0, 0))
    target[key] = (message_count + 1, event_count + event_weight)


def build_daily_rows(
    start_date: date,
    end_date: date,
    counts: Dict[date, Tuple[int, int]],
) -> List[dict]:
    """Build zero-filled daily rows."""
    rows = []
    for day in iter_dates(start_date, end_date):
        message_count, event_count = counts.get(day, (0, 0))
        rows.append(
            {
                "date_berlin": day.isoformat(),
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def build_weekday_rows(
    start_date: date,
    end_date: date,
    counts: Dict[int, Tuple[int, int]],
) -> List[dict]:
    """Build weekday totals and means."""
    occurrences = {idx: 0 for idx in range(7)}
    for day in iter_dates(start_date, end_date):
        occurrences[day.weekday()] += 1

    rows = []
    for idx in range(7):
        message_count, event_count = counts.get(idx, (0, 0))
        occ = occurrences[idx]
        rows.append(
            {
                "weekday": weekday_name(idx),
                "weekday_idx": idx,
                "check_message_count": message_count,
                "check_event_count": event_count,
                "weekday_occurrences": occ,
                "mean_messages_per_weekday": round(message_count / occ, 6) if occ else 0.0,
                "mean_events_per_weekday": round(event_count / occ, 6) if occ else 0.0,
            }
        )
    return rows


def build_hour_rows(counts: Dict[int, Tuple[int, int]]) -> List[dict]:
    """Build hourly totals."""
    rows = []
    for hour in range(24):
        message_count, event_count = counts.get(hour, (0, 0))
        rows.append(
            {
                "hour": hour,
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def build_week_of_month_rows(counts: Dict[int, Tuple[int, int]]) -> List[dict]:
    """Build week-of-month totals (1-5)."""
    rows = []
    for week in range(1, 6):
        message_count, event_count = counts.get(week, (0, 0))
        rows.append(
            {
                "week_of_month_simple": week,
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def build_month_week_rows(
    counts: Dict[Tuple[str, int], Tuple[int, int]]
) -> List[dict]:
    """Build month x week-of-month counts."""
    rows = []
    for (month, week), (message_count, event_count) in sorted(counts.items()):
        rows.append(
            {
                "month": month,
                "week_of_month_simple": week,
                "check_message_count": message_count,
                "check_event_count": event_count,
            }
        )
    return rows


def build_month_rows(
    start_date: date,
    end_date: date,
    counts: Dict[str, Tuple[int, int]],
) -> List[dict]:
    """Build month totals and normalized rates."""
    days_in_month: Dict[str, int] = {}
    for day in iter_dates(start_date, end_date):
        month = f"{day.year:04d}-{day.month:02d}"
        days_in_month[month] = days_in_month.get(month, 0) + 1

    rows = []
    for month, days in sorted(days_in_month.items()):
        message_count, event_count = counts.get(month, (0, 0))
        total_days_in_month = days_in_calendar_month(month)
        rows.append(
            {
                "month": month,
                "month_message_count": message_count,
                "month_event_count": event_count,
                "days_in_month_in_range": days,
                "is_partial_month": days < total_days_in_month,
                "messages_per_day_in_month": round(message_count / days, 6) if days else 0.0,
                "events_per_day_in_month": round(event_count / days, 6) if days else 0.0,
            }
        )
    return rows


def days_in_calendar_month(month: str) -> int:
    """Return the number of days in a YYYY-MM month string."""
    year, month_num = (int(part) for part in month.split("-"))
    if month_num == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month_num + 1, 1)
    current_month = date(year, month_num, 1)
    return (next_month - current_month).days


def write_events_csv(path: Path, events: List[Dict[str, Any]]) -> None:
    """Write events.csv with deterministic ordering."""
    fieldnames = [
        "event_id",
        "message_id",
        "timestamp_utc",
        "timestamp_berlin",
        "date_berlin",
        "weekday",
        "weekday_idx",
        "iso_year",
        "iso_week",
        "month",
        "time_berlin",
        "hour",
        "week_of_month_simple",
        "match_type",
        "event_weight",
        "matched_k_values",
        "matched_keywords",
        "k_token_hit_count",
        "confidence_score",
        "k_min",
        "k_max",
        "k_qualifier",
        "control_keyword_hit",
        "control_keyword_forms",
        "line_id",
        "mode_guess",
        "line_validated",
        "line_confidence",
        "direction_text",
        "direction_polarity",
        "location_text",
        "platform_text",
        "stitched_message_ids",
        "text_trunc",
        "text_len",
        "text_sha256",
    ]
    write_csv(path, events, fieldnames)


def sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file_hex(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return SHA-256 hex digest of a file by streaming bytes."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_metadata(
    input_path: Path,
    config: AnalyzeConfig,
    counts: Dict[str, int],
    dataset_start: date,
    dataset_end: date,
    *,
    started_utc: datetime,
    completed_utc: datetime,
    tg_checkstats_argv: List[str] | None = None,
    telegram_download_chat_argv: List[str] | None = None,
    export_retry_count: int | None = None,
    export_retry_delay_seconds: int | None = None,
) -> Dict[str, Any]:
    """Build run metadata payload."""
    return {
        "tool_versions": {
            "telegram_download_chat": None,
            "analyzer": __version__,
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "timestamps": {
            "analyze_started_utc": started_utc.isoformat().replace("+00:00", "Z"),
            "analyze_completed_utc": completed_utc.isoformat().replace("+00:00", "Z"),
        },
        "commands": {
            "tg_checkstats_argv": tg_checkstats_argv,
            "telegram_download_chat_argv": telegram_download_chat_argv,
        },
        "input": {
            "chat_identifier_raw": None,
            "chat_identifier_normalized": None,
            "raw_export_path": str(input_path),
            "raw_export_sha256": sha256_file_hex(input_path),
        },
        "config": {
            "timezone": "Europe/Berlin",
            "k_max": 20,
            "keywords": ["Kontrollettis", "Kontrolleure", "Kontis"],
            "event_count_policy": config.event_count_policy,
            "include_service": config.include_service,
            "include_bots": config.include_bots,
            "include_forwards": config.include_forwards,
            "export_retry_count": export_retry_count,
            "export_retry_delay_seconds": export_retry_delay_seconds,
            "text_trunc_len": config.text_trunc_len,
        },
        "auth": {
            "api_id_last4": None,
            "api_hash_present": False,
            "api_hash_sha256_prefix": None,
        },
        "counts": counts,
        "dataset": {
            "start_berlin_date": dataset_start.isoformat(),
            "end_berlin_date": dataset_end.isoformat(),
            "total_days_in_range": (dataset_end - dataset_start).days + 1,
        },
        "assumptions": {
            "naive_timestamps_treated_as_utc": True,
            "naive_timestamp_count": counts.get("naive_timestamp_count", 0),
        },
    }
