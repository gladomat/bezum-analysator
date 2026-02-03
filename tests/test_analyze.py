"""Analyzer pipeline tests."""

from __future__ import annotations

from datetime import datetime
import json
import hashlib
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


def _parse_zulu(value: str) -> datetime:
    """Parse an ISO-8601 timestamp with trailing Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_run_metadata_contains_streaming_sha256_and_monotonic_timestamps(
    tmp_path: Path,
    monkeypatch,
):
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-02T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_bytes = json.dumps(data).encode("utf-8")
    export_path.write_bytes(export_bytes)

    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args, **kwargs) -> str:
        if self == export_path:
            raise AssertionError("analyze_export should not read the raw export as text")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    metadata = analyze_export(export_path, tmp_path)

    expected_sha256 = hashlib.sha256(export_bytes).hexdigest()
    assert metadata["input"]["raw_export_sha256"] == expected_sha256

    started = _parse_zulu(metadata["timestamps"]["analyze_started_utc"])
    completed = _parse_zulu(metadata["timestamps"]["analyze_completed_utc"])
    assert completed >= started


def test_analyze_supports_ndjson_input(tmp_path: Path):
    export_path = tmp_path / "export.ndjson"
    export_path.write_text(
        "\n".join(
            [
                json.dumps({"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"}),
                json.dumps({"id": 2, "date": "2024-01-02T08:00:00Z", "text": "Kontis"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analyze_export(export_path, tmp_path)

    events_path = tmp_path / "derived" / "events.csv"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + 2 events
