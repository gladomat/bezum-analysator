"""Known LVB line universe for Leipzig (tram, bus, nightliner).

This module provides a conservative, curated set of line identifiers used to
validate inferred line mentions in chat messages. The intent is to reduce false
positives from bare numbers (e.g., platform numbers, times, counts).

Source (snapshot): LVB "Fahrpläne zum Download" select options.
Fetched: 2026-02-05.
"""

from __future__ import annotations


TRAM_LINES: frozenset[str] = frozenset(
    {
        "1",
        "2",
        "3",
        "4",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "14",
        "15",
        "16",
    }
)

BUS_LINES: frozenset[str] = frozenset(
    {
        "60",
        "61",
        "62",
        "63",
        "65",
        "66",
        "67",
        "70",
        "71",
        "72",
        "73",
        "74",
        "75",
        "76",
        "77",
        "79",
        "80",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "90",
        "91",
        "E",
    }
)

REGIONALBUS_LINES: frozenset[str] = frozenset(
    {
        "108",
        "131",
        "143",
        "162",
        "172",
        "173",
        "175",
        "176",
    }
)

NIGHTLINER_LINES: frozenset[str] = frozenset(
    {
        "N1",
        "N2",
        "N3",
        "N4",
        "N5",
        "N6",
        "N7",
        "N8",
        "N9",
        "N10",
        "N17",
        "N60",
        "NXL",
    }
)


def normalize_line_id(value: str) -> str:
    """Normalize a line identifier (trim + uppercase)."""
    return value.strip().upper()


def is_valid_line_id(line_id: str) -> bool:
    """Return True if line_id is in the known line universe.

    Accepts *E variants (e.g., 11E) if the base line is known. These show up in
    real exports (replacement lines / special variants) even if not listed as
    selectable timetable IDs.
    """
    normalized = normalize_line_id(line_id)
    known = TRAM_LINES | BUS_LINES | REGIONALBUS_LINES | NIGHTLINER_LINES
    if normalized in known:
        return True
    if normalized != "E" and normalized.endswith("E"):
        base = normalized[:-1]
        return base in known
    return False


def guess_mode(line_id: str, explicit_mode: str | None = None) -> str:
    """Guess transport mode from the line id (optionally overriding by explicit label)."""
    if explicit_mode in {"tram", "bus", "sev"}:
        return explicit_mode

    normalized = normalize_line_id(line_id)
    if normalized != "E" and normalized.endswith("E"):
        normalized = normalized[:-1]
    if normalized in TRAM_LINES:
        return "tram"
    if normalized in NIGHTLINER_LINES:
        return "night"
    if normalized in BUS_LINES or normalized in REGIONALBUS_LINES:
        return "bus"
    return "unknown"
