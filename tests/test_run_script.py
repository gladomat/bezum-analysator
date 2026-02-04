"""Tests for the helper run script."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_run_script_creates_run_dir_and_invokes_commands(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    env = {
        "RUNS_DIR": str(runs_dir),
        "RUN_ID": "testid",
        "EXPORT_LIMIT": "10",
        "TELEGRAM_DOWNLOAD_CHAT_BIN": "/bin/echo",
        "PYTHON_BIN": "/bin/echo",
        "ANALYZE_FORCE_AUTO": "1",
    }

    result = subprocess.run(
        ["bash", "scripts/tg_checkstats_run.sh", "https://t.me/example_channel"],
        check=False,
        capture_output=True,
        text=True,
        env={**env, **dict(**__import__("os").environ)},
    )
    assert result.returncode == 0, result.stderr

    run_dir = runs_dir / "example_channel_testid"
    assert (run_dir / "raw").is_dir()

    combined = result.stdout + result.stderr
    assert "run_dir=" in combined
    assert "-l 10" in combined
    assert "tg_checkstats analyze" in combined
