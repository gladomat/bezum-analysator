"""Export integration with telegram-download-chat."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import List

from dotenv import load_dotenv


def build_export_command(
    chat: str,
    output_path: str,
    retry_count: int,
    retry_delay_seconds: int,
    config_path: str | None = None,
) -> List[str]:
    """Build the telegram-download-chat CLI command."""
    cmd = [
        "telegram-download-chat",
        "--chat",
        chat,
        "--output",
        output_path,
        "--format",
        "json",
        "--retry-count",
        str(retry_count),
        "--retry-delay",
        str(retry_delay_seconds),
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    return cmd


def run_export(chat: str, output_path: Path, retry_count: int, retry_delay_seconds: int) -> List[str]:
    """Run telegram-download-chat with a temporary config file."""
    load_dotenv()

    config_path = write_temp_config()
    cmd = build_export_command(
        chat,
        str(output_path),
        retry_count,
        retry_delay_seconds,
        config_path=config_path,
    )
    subprocess.run(cmd, check=True)
    return cmd


def write_temp_config() -> str:
    """Write a temporary config file for telegram-download-chat."""
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    handle.write("{}")
    handle.flush()
    return handle.name
