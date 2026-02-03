"""Export integration tests."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from tg_checkstats.export import build_export_command, run_export


def test_build_export_command():
    cmd = build_export_command("mychat", "/tmp/out.json")
    assert cmd[0] == "telegram-download-chat"
    assert cmd[1] == "mychat"
    assert "--output" in cmd
    assert "/tmp/out.json" in cmd


def test_run_export_retries_on_failure(tmp_path: Path, monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        calls.append(cmd)
        if len(calls) < 3:
            raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("tg_checkstats.export.time.sleep", lambda *_args, **_kwargs: None)

    cmd = run_export("mychat", tmp_path / "export.json", retry_count=3, retry_delay_seconds=5)
    assert cmd[0] == "telegram-download-chat"
    assert len(calls) == 3


def test_run_export_raises_after_exhausting_retries(tmp_path: Path, monkeypatch):
    def fake_run(cmd: list[str], check: bool) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("tg_checkstats.export.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(subprocess.CalledProcessError):
        run_export("mychat", tmp_path / "export.json", retry_count=2, retry_delay_seconds=0)
