"""Web UI artifact + API shaping tests."""

from __future__ import annotations

from datetime import date
import csv
import json
from pathlib import Path

from tg_checkstats.analyze import analyze_export


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read all rows from a CSV file as dicts."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def test_analyze_writes_ui_artifacts_with_both_metrics(tmp_path: Path) -> None:
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-01T11:00:00Z", "text": "nope"},
        {"id": 3, "date": "2024-01-02T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data), encoding="utf-8")

    analyze_export(export_path, tmp_path)

    ui_dir = tmp_path / "derived" / "ui"
    assert (ui_dir / "month_counts.csv").exists()
    assert (ui_dir / "day_counts.csv").exists()
    assert (ui_dir / "day_hour_counts.csv").exists()
    assert (ui_dir / "month_weekday_stats.csv").exists()
    assert (ui_dir / "calendar_day_index.csv").exists()

    day_rows = _read_csv_rows(ui_dir / "day_counts.csv")
    assert len(day_rows) >= 2
    assert {"check_message_count", "check_event_count"}.issubset(day_rows[0].keys())

    hour_rows = _read_csv_rows(ui_dir / "day_hour_counts.csv")
    assert {"date", "hour", "check_message_count", "check_event_count"}.issubset(hour_rows[0].keys())


def test_week_api_payload_has_7_days_and_24_bins(tmp_path: Path) -> None:
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-02T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data), encoding="utf-8")
    analyze_export(export_path, tmp_path)

    from tg_checkstats.web_ui import UiArtifacts  # import after artifacts exist

    artifacts = UiArtifacts(tmp_path)
    payload = artifacts.get_week("2024-01-01")

    assert payload["week_start_date"] == "2024-01-01"
    assert len(payload["days"]) == 7
    for day in payload["days"]:
        assert {"check_message_count", "check_event_count"}.issubset(day.keys())
        assert len(day["hours"]) == 24
        for hour in day["hours"]:
            assert {"hour", "check_message_count", "check_event_count"}.issubset(hour.keys())


def test_month_api_payload_contains_week_grid(tmp_path: Path) -> None:
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-10T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data), encoding="utf-8")
    analyze_export(export_path, tmp_path)

    from tg_checkstats.web_ui import UiArtifacts  # import after artifacts exist

    artifacts = UiArtifacts(tmp_path)
    payload = artifacts.get_month("2024-01")

    assert payload["month"] == "2024-01"
    assert payload["weeks"]
    assert payload["grid"]
    assert payload["weekday_stats"]

    cell = payload["grid"][0]
    assert {"date", "week_start_date", "weekday_idx", "in_month"}.issubset(cell.keys())
    assert {"check_message_count", "check_event_count"}.issubset(cell.keys())

