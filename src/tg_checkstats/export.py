"""Export integration with telegram-download-chat."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import tempfile
import time
from typing import List

from dotenv import load_dotenv


def build_export_command(
    chat: str,
    output_path: str,
    config_path: str | None = None,
) -> List[str]:
    """Build the telegram-download-chat CLI command."""
    cmd = ["telegram-download-chat", chat, "--output", output_path]
    if config_path:
        cmd.extend(["--config", config_path])
    return cmd


def run_export(chat: str, output_path: Path, retry_count: int, retry_delay_seconds: int) -> List[str]:
    """Run telegram-download-chat, optionally retrying failures.

    If `api_id`/`api_hash` (or `API_ID`/`API_HASH`) are present in the environment,
    write a temporary config and pass it via `--config`.
    """
    load_dotenv()

    config_path: str | None = None
    try:
        creds = resolve_api_credentials()
        if creds is not None:
            api_id, api_hash = creds
            config_path = write_temp_config(api_id=api_id, api_hash=api_hash)

        cmd = build_export_command(chat, str(output_path), config_path=config_path)

        last_exc: subprocess.CalledProcessError | None = None
        attempts = max(1, int(retry_count))
        for attempt_idx in range(attempts):
            try:
                subprocess.run(cmd, check=True)
                return cmd
            except subprocess.CalledProcessError as exc:
                last_exc = exc
                if attempt_idx == attempts - 1:
                    raise
                time.sleep(max(0, int(retry_delay_seconds)))
        raise last_exc  # pragma: no cover
    finally:
        if config_path:
            try:
                os.unlink(config_path)
            except FileNotFoundError:
                pass


def resolve_api_credentials() -> tuple[str, str] | None:
    """Return (api_id, api_hash) from the environment if present."""
    api_id = os.environ.get("api_id") or os.environ.get("API_ID")
    api_hash = os.environ.get("api_hash") or os.environ.get("API_HASH")
    if not api_id or not api_hash:
        return None
    return api_id, api_hash


def write_temp_config(*, api_id: str, api_hash: str) -> str:
    """Write a temporary YAML config file for telegram-download-chat."""
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
    handle.write(
        "\n".join(
            [
                "settings:",
                f"  api_id: {api_id}",
                f"  api_hash: {api_hash}",
                "",
            ]
        )
    )
    handle.flush()
    return handle.name
