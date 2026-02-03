"""Command-line interface for tg-checkstats."""

from __future__ import annotations

from pathlib import Path
import shutil
import sys

import click

from tg_checkstats.analyze import AnalyzeConfig, analyze_export
from tg_checkstats.export import run_export


@click.group()
def app() -> None:
    """tg-checkstats CLI."""


@app.command()
@click.option("--chat", required=True, help="Public chat name or link.")
@click.option("--out", "out_dir", required=True, type=click.Path(path_type=Path))
@click.option("--export-retry-count", default=3, type=int, show_default=True)
@click.option("--export-retry-delay", default=5, type=int, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite derived/logs outputs.")
def export(chat: str, out_dir: Path, export_retry_count: int, export_retry_delay: int, force: bool) -> None:
    """Export a Telegram chat history."""
    prepare_out_dir(out_dir, force=force, for_export=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "export.json"
    if output_path.exists():
        raise SystemExit("raw export already exists; choose a new run name or remove raw export")
    run_export(chat, output_path, export_retry_count, export_retry_delay)


@app.command()
@click.option("--input", "input_path", required=True, type=click.Path(path_type=Path))
@click.option("--out", "out_dir", required=True, type=click.Path(path_type=Path))
@click.option("--event-count-policy", default="message", type=click.Choice(["message", "token"]))
@click.option("--include-service", is_flag=True, default=False)
@click.option("--include-bots/--exclude-bots", default=True, show_default=True)
@click.option("--include-forwards/--exclude-forwards", default=True, show_default=True)
@click.option("--text-trunc-len", default=500, type=int, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite derived/logs outputs.")
def analyze(
    input_path: Path,
    out_dir: Path,
    event_count_policy: str,
    include_service: bool,
    include_bots: bool,
    include_forwards: bool,
    text_trunc_len: int,
    force: bool,
) -> None:
    """Analyze a chat export."""
    prepare_out_dir(out_dir, force=force, for_export=False)
    cfg = AnalyzeConfig(
        event_count_policy=event_count_policy,
        include_service=include_service,
        include_bots=include_bots,
        include_forwards=include_forwards,
        text_trunc_len=text_trunc_len,
    )
    analyze_export(input_path, out_dir, cfg, tg_checkstats_argv=sys.argv)


@app.command()
@click.option("--chat", required=True, help="Public chat name or link.")
@click.option("--out", "out_dir", required=True, type=click.Path(path_type=Path))
@click.option("--export-retry-count", default=3, type=int, show_default=True)
@click.option("--export-retry-delay", default=5, type=int, show_default=True)
@click.option("--event-count-policy", default="message", type=click.Choice(["message", "token"]))
@click.option("--include-service", is_flag=True, default=False)
@click.option("--include-bots/--exclude-bots", default=True, show_default=True)
@click.option("--include-forwards/--exclude-forwards", default=True, show_default=True)
@click.option("--text-trunc-len", default=500, type=int, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite derived/logs outputs.")
def run(
    chat: str,
    out_dir: Path,
    export_retry_count: int,
    export_retry_delay: int,
    event_count_policy: str,
    include_service: bool,
    include_bots: bool,
    include_forwards: bool,
    text_trunc_len: int,
    force: bool,
) -> None:
    """Export and analyze a chat history."""
    prepare_out_dir(out_dir, force=force, for_export=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "export.json"
    if output_path.exists():
        raise SystemExit("raw export already exists; choose a new run name or remove raw export")
    export_cmd = run_export(chat, output_path, export_retry_count, export_retry_delay)
    cfg = AnalyzeConfig(
        event_count_policy=event_count_policy,
        include_service=include_service,
        include_bots=include_bots,
        include_forwards=include_forwards,
        text_trunc_len=text_trunc_len,
    )
    analyze_export(
        output_path,
        out_dir,
        cfg,
        tg_checkstats_argv=sys.argv,
        telegram_download_chat_argv=export_cmd,
        export_retry_count=export_retry_count,
        export_retry_delay_seconds=export_retry_delay,
    )


def prepare_out_dir(out_dir: Path, force: bool, for_export: bool) -> None:
    """Prepare the run directory according to --force behavior."""
    derived_dir = out_dir / "derived"
    logs_dir = out_dir / "logs"
    raw_dir = out_dir / "raw"

    if for_export and raw_dir.exists() and any(raw_dir.iterdir()):
        raise SystemExit("raw export already exists; choose a new run name or remove raw export")

    if force:
        if derived_dir.exists():
            shutil.rmtree(derived_dir)
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
    else:
        if derived_dir.exists() and any(derived_dir.iterdir()):
            raise SystemExit("derived outputs already exist; use --force or choose a new run name")
        if logs_dir.exists() and any(logs_dir.iterdir()):
            raise SystemExit("logs already exist; use --force or choose a new run name")

    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    app()
