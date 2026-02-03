"""Project-level sanity checks."""

from __future__ import annotations

from pathlib import Path


def test_readme_exists_at_repo_root():
    """Ensure packaging metadata references an existing README.md."""
    assert Path("README.md").exists()
