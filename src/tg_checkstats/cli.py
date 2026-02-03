"""Command-line interface for tg-checkstats."""

from __future__ import annotations

import click


@click.group()
def app() -> None:
    """tg-checkstats CLI."""


@app.command()
def export() -> None:
    """Export a Telegram chat history."""
    raise SystemExit("export not implemented")


@app.command()
def analyze() -> None:
    """Analyze a chat export."""
    raise SystemExit("analyze not implemented")


@app.command()
def run() -> None:
    """Export and analyze a chat history."""
    raise SystemExit("run not implemented")


if __name__ == "__main__":
    app()
