"""Parsing helpers for exports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Tuple

from dateutil import parser


def normalize_text(value: Any) -> str:
    """Normalize text/caption values into a plain string."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "".join(parts)
    return ""


def parse_timestamp(value: Any) -> Tuple[datetime, bool]:
    """Parse timestamps from ISO strings or epoch seconds.

    Returns a tuple of (datetime, assumed_utc).
    """
    if value is None:
        raise ValueError("timestamp is missing")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc), False
    if isinstance(value, str):
        dt = parser.isoparse(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc), True
        return dt.astimezone(timezone.utc), False
    raise TypeError(f"unsupported timestamp type: {type(value)!r}")
