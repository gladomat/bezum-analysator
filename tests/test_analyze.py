"""Analyzer pipeline tests."""

import json
from pathlib import Path

from tg_checkstats.analyze import analyze_export


def test_analyze_minimal(tmp_path: Path):
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-01T11:00:00Z", "text": "nope"},
        {"id": 3, "date": "2024-01-02T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data))

    analyze_export(export_path, tmp_path)

    events_path = tmp_path / "derived" / "events.csv"
    assert events_path.exists()
    lines = events_path.read_text().splitlines()
    assert len(lines) == 3  # header + 2 events
