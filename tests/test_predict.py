"""Predictor API + aggregation tests."""

from __future__ import annotations

import json
from pathlib import Path

from tg_checkstats.analyze import analyze_export


def test_predictor_hourly_probabilities_use_day_hour_buckets(tmp_path: Path) -> None:
    """Probability is computed on ">=1 event in (date,hour)" buckets."""
    data = [
        # Monday (Berlin hour=10)
        {"id": 1, "date": "2024-01-01T10:00:00+01:00", "text": "2k tram 10"},
        # Monday (Berlin hour=10)
        {"id": 2, "date": "2024-01-08T10:00:00+01:00", "text": "Kontis tram 10"},
        # Extend dataset range to include 2024-01-15 (also Monday)
        {"id": 3, "date": "2024-01-15T10:00:00+01:00", "text": "nope"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data), encoding="utf-8")
    analyze_export(export_path, tmp_path)

    from tg_checkstats.web_ui import UiArtifacts  # import after artifacts exist

    artifacts = UiArtifacts(tmp_path)
    payload = artifacts.get_predict_line(line_id="10", mode="tram", weekday_idx=0)

    assert payload["line_id"] == "10"
    assert payload["mode"] == "tram"
    assert payload["weekday_idx"] == 0
    assert len(payload["hours"]) == 24

    h10 = next((r for r in payload["hours"] if int(r["hour"]) == 10), None)
    assert h10 is not None
    assert h10["trials"] == 3
    assert h10["successes"] == 2
    assert 0.0 <= float(h10["prob_mean"]) <= 1.0
    assert 0.0 <= float(h10["prob_low"]) <= float(h10["prob_high"]) <= 1.0

