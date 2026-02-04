"""CLI tests."""

from __future__ import annotations

from pathlib import Path

import tg_checkstats.cli as cli_mod


def test_cli_help_shows_commands(runner, cli):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output
    assert "analyze" in result.output
    assert "run" in result.output
    assert "serve" in result.output


def test_export_refuses_overwrite_existing_raw_export(
    tmp_path: Path,
    runner,
    cli,
    monkeypatch,
):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "export.json").write_text("[]", encoding="utf-8")

    called = False

    def fake_run_export(*_args, **_kwargs) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_mod, "run_export", fake_run_export)

    result = runner.invoke(cli, ["export", "--chat", "example", "--out", str(tmp_path)])
    assert result.exit_code != 0
    assert "raw export already exists" in (result.output + str(result.exception))
    assert called is False


def test_export_refuses_overwrite_existing_raw_export_even_with_force(
    tmp_path: Path,
    runner,
    cli,
    monkeypatch,
):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "export.json").write_text("[]", encoding="utf-8")

    called = False

    def fake_run_export(*_args, **_kwargs) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_mod, "run_export", fake_run_export)

    result = runner.invoke(cli, ["export", "--chat", "example", "--out", str(tmp_path), "--force"])
    assert result.exit_code != 0
    assert "raw export already exists" in (result.output + str(result.exception))
    assert called is False
