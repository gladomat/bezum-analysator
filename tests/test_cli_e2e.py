"""End-to-end CLI tests."""

import json
from pathlib import Path


def test_analyze_command(tmp_path: Path, runner, cli):
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
        {"id": 2, "date": "2024-01-02T08:00:00Z", "text": "Kontis"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data))

    result = runner.invoke(
        cli,
        ["analyze", "--input", str(export_path), "--out", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert (tmp_path / "derived" / "events.csv").exists()


def test_analyze_refuses_overwrite_derived_without_force(tmp_path: Path, runner, cli):
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data))

    first = runner.invoke(cli, ["analyze", "--input", str(export_path), "--out", str(tmp_path)])
    assert first.exit_code == 0

    second = runner.invoke(cli, ["analyze", "--input", str(export_path), "--out", str(tmp_path)])
    assert second.exit_code != 0
    assert "derived" in (second.output + str(second.exception))


def test_analyze_allows_overwrite_derived_with_force(tmp_path: Path, runner, cli):
    data = [
        {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(data))

    first = runner.invoke(cli, ["analyze", "--input", str(export_path), "--out", str(tmp_path)])
    assert first.exit_code == 0

    second = runner.invoke(cli, ["analyze", "--input", str(export_path), "--out", str(tmp_path), "--force"])
    assert second.exit_code == 0
