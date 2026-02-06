"""Gunicorn WSGI entrypoint for tg-checkstats.

Render (and most PaaS providers) expect a long-running process that binds to
`$PORT`. For production-like deployments we serve the existing WSGI app created
by `tg_checkstats.web_server.create_app` using Gunicorn.

Environment:
  - TG_CHECKSTATS_RUN_DIR: Writable path used as the active "current run".
    Uploaded exports are analyzed into sibling directories under
    `<TG_CHECKSTATS_RUN_DIR>/../uploaded/`.
"""

from __future__ import annotations

import os
from pathlib import Path

from tg_checkstats.web_server import create_app


def _resolve_run_dir() -> Path:
    """Resolve the configured run directory path for the web service.

    Returns:
        A filesystem path where the web service can read/write run artifacts.
    """
    raw = os.environ.get("TG_CHECKSTATS_RUN_DIR", "").strip()
    if not raw:
        return Path("/tmp/tg-checkstats/run/current")
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


_RUN_DIR = _resolve_run_dir()
_RUN_DIR.mkdir(parents=True, exist_ok=True)

# Gunicorn default: `module:app`
app = create_app(run_dir=_RUN_DIR)

