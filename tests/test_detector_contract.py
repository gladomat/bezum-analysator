"""Detector contract upgrade tests (v1.0.1-ish).

These tests cover real-world message forms seen in the Leipzig "check" chats:
- k-count ranges (e.g. 3-5k, 4/5 k)
- plural/unknown k mentions (e.g. "Mehrere Ks")
- keyword variants (Kontrolle, Kontrolleuren, Kontrolleur*innen, ...)
- line + direction + location/platform extraction
"""

from __future__ import annotations

import json
from pathlib import Path

from tg_checkstats.analyze import analyze_export
from tg_checkstats.detector import detect_event


def test_detect_event_extracts_range_k_count():
    info = detect_event("3-5 k am hbf")
    assert info["is_check_event"] is True
    assert info["k_min"] == 3
    assert info["k_max"] == 5
    assert info["k_qualifier"] == "range"
    assert info["match_type"] == "k_token"
    assert info["matched_k_values"] == [3, 5]


def test_detect_event_extracts_multiple_unknown_k_mentions():
    info = detect_event("Mehrere Ks am Hbf")
    assert info["is_check_event"] is True
    assert info["k_min"] is None
    assert info["k_max"] is None
    assert info["k_qualifier"] == "multiple"
    assert info["match_type"] == "k_token"


def test_detect_event_matches_control_keyword_variants():
    info = detect_event("kontrolleuren am hbf")
    assert info["is_check_event"] is True
    assert info["match_type"] == "keyword"
    assert info["control_keyword_hit"] is True
    assert any("kontroll" in form.lower() for form in info["control_keyword_forms"])


def test_detect_event_extracts_line_direction_location_and_platform():
    info = detect_event("2k am Hbf, Steig C in der 10 Richtung Lößnig")
    assert info["is_check_event"] is True
    assert info["line_id"] == "10"
    assert info["line_validated"] is True
    assert info["mode_guess"] in {"tram", "bus", "night", "sev", "unknown"}
    assert info["direction_text"].lower().startswith("lö")
    assert info["location_text"].lower().startswith("hbf")
    assert info["platform_text"].lower() in {"steig c", "gleis c"}


def test_line_and_direction_alone_counts_as_check():
    info = detect_event("11 stadteinwärts s bhf connewitz jetzt.")
    assert info["is_check_event"] is True
    assert info["line_id"] == "11"
    assert info["line_validated"] is True
    assert info["direction_polarity"] == "inbound"


def test_e_suffix_lines_validate_via_base_line():
    info = detect_event("11E Richtung Dölitz")
    assert info["is_check_event"] is True
    assert info["line_id"] == "11E"
    assert info["line_validated"] is True
    assert info["mode_guess"] in {"tram", "bus", "night", "sev", "unknown"}


def test_analyze_stitches_followup_direction_into_previous_event(tmp_path: Path):
    data = [
        {"id": 1, "from_id": 111, "date": "2024-01-01T10:00:00Z", "text": "2k am hbf"},
        {"id": 2, "from_id": 111, "date": "2024-01-01T10:03:00Z", "text": "Richtung: Stadteinwärts"},
        {"id": 3, "from_id": 222, "date": "2024-01-01T10:04:00Z", "text": "Richtung: Stadteinwärts"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data), encoding="utf-8")

    analyze_export(export_path, tmp_path)

    events_path = tmp_path / "derived" / "events.csv"
    rows = events_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2  # header + 1 check event row (direction-only followups excluded)

    header = rows[0].split(",")
    assert "direction_polarity" in header
    assert "stitched_message_ids" in header

    values = rows[1].split(",")
    row = dict(zip(header, values))
    assert row["direction_polarity"] == "inbound"
    assert row["stitched_message_ids"] == "[2]"
