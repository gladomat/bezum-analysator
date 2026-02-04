"""Local web UI server for tg-checkstats (static SPA + small JSON API).

This is intentionally dependency-free (stdlib only) to keep the tool low-friction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple
from wsgiref.simple_server import make_server

from tg_checkstats.web_ui import UiArtifacts


_REQUIRED_UI_FILES = [
    "run_metadata.json",
    "derived/ui/month_counts.csv",
    "derived/ui/day_counts.csv",
    "derived/ui/day_hour_counts.csv",
    "derived/ui/month_weekday_stats.csv",
    "derived/ui/calendar_day_index.csv",
]


def serve_web_ui(*, run_dir: Path, host: str, port: int) -> None:
    """Start the local Web UI server for a given run directory."""
    app = create_app(run_dir=run_dir)
    with make_server(host, port, app) as httpd:
        url = f"http://{host}:{port}/"
        print(f"Serving tg-checkstats UI for {run_dir} at {url}")
        httpd.serve_forever()


def create_app(*, run_dir: Path) -> Callable:
    """Create a WSGI application bound to a specific run directory."""
    static_dir = Path(__file__).with_name("web_assets")

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/") or "/"
        if path.startswith("/api/"):
            status, headers, body = handle_api(run_dir=run_dir, path=path)
        elif path.startswith("/assets/"):
            rel = path.removeprefix("/assets/")
            status, headers, body = serve_static(static_dir=static_dir, rel_path=rel)
        else:
            status, headers, body = serve_static(static_dir=static_dir, rel_path="index.html")

        start_response(status, headers)
        return [body]

    return app


def _artifact_presence(run_dir: Path) -> Tuple[Dict[str, bool], list[str]]:
    """Return (presence_map, missing_list) for required UI files."""
    presence: Dict[str, bool] = {}
    missing: list[str] = []
    for rel in _REQUIRED_UI_FILES:
        ok = (run_dir / rel).exists()
        presence[rel] = ok
        if not ok:
            missing.append(rel)
    return presence, missing


def handle_api(*, run_dir: Path, path: str) -> tuple[str, list[tuple[str, str]], bytes]:
    """Handle `/api/*` routes."""
    presence, missing = _artifact_presence(run_dir)

    if path == "/api/run":
        payload = {
            "run_dir": str(run_dir),
            "run_id": run_dir.name,
            "required_files": list(_REQUIRED_UI_FILES),
            "artifacts_present": presence,
            "missing_files": missing,
            "default_metric": "check_message_count",
            "available_metrics": ["check_message_count", "check_event_count"],
        }
        if presence.get("run_metadata.json"):
            try:
                artifacts = UiArtifacts(run_dir)
                cfg = artifacts.metadata.get("config") if isinstance(artifacts.metadata, dict) else None
                tz = cfg.get("timezone") if isinstance(cfg, dict) else None
                payload["timezone"] = tz or "Europe/Berlin"
                payload["dataset"] = {
                    "start_date": artifacts.dataset_range.start.isoformat(),
                    "end_date": artifacts.dataset_range.end.isoformat(),
                }
            except Exception:
                pass
        return json_response(payload)

    if missing:
        return json_response(
            {"error": "missing_ui_artifacts", "missing_files": missing},
            status="400 Bad Request",
        )

    artifacts = UiArtifacts(run_dir)
    if path == "/api/months":
        return json_response(artifacts.get_months())
    if path.startswith("/api/month/"):
        month = path.removeprefix("/api/month/").strip("/")
        return json_response(artifacts.get_month(month))
    if path.startswith("/api/week/"):
        week_start_date = path.removeprefix("/api/week/").strip("/")
        try:
            return json_response(artifacts.get_week(week_start_date))
        except ValueError as exc:
            return json_response({"error": str(exc)}, status="400 Bad Request")

    return json_response({"error": "not_found"}, status="404 Not Found")


def json_response(payload: object, *, status: str = "200 OK") -> tuple[str, list[tuple[str, str]], bytes]:
    """Return a JSON WSGI response."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", "no-store"),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, body


def serve_static(*, static_dir: Path, rel_path: str) -> tuple[str, list[tuple[str, str]], bytes]:
    """Serve a static asset from the packaged `web_assets/` directory."""
    path = (static_dir / rel_path).resolve()
    if not str(path).startswith(str(static_dir.resolve())):
        return "403 Forbidden", [("Content-Type", "text/plain; charset=utf-8")], b"forbidden"

    if not path.exists() or not path.is_file():
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"not found"

    content_type = "text/plain; charset=utf-8"
    if path.suffix == ".html":
        content_type = "text/html; charset=utf-8"
    elif path.suffix == ".css":
        content_type = "text/css; charset=utf-8"
    elif path.suffix == ".js":
        content_type = "text/javascript; charset=utf-8"
    elif path.suffix == ".png":
        content_type = "image/png"

    body = path.read_bytes()
    headers = [
        ("Content-Type", content_type),
        ("Cache-Control", "no-store"),
        ("Content-Length", str(len(body))),
    ]
    return "200 OK", headers, body

