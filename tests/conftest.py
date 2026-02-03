"""Pytest fixtures for tg-checkstats."""

from __future__ import annotations

from pathlib import Path
import sys

from click.testing import CliRunner
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tg_checkstats.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    """Provide a Click CLI runner."""
    return CliRunner()


@pytest.fixture()
def cli():
    """Provide the CLI app entrypoint."""
    return app
