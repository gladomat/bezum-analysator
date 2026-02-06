"""Local web UI server for tg-checkstats (static SPA + small JSON API).

This is intentionally dependency-free (stdlib only) to keep the tool low-friction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple
from wsgiref.simple_server import make_server

from tg_checkstats.analyze import analyze_export
from tg_checkstats.web_ui import UiArtifacts


_REQUIRED_UI_FILES = [
    "run_metadata.json",
    "derived/ui/month_counts.csv",
    "derived/ui/day_counts.csv",
    "derived/ui/day_hour_counts.csv",
    "derived/ui/month_weekday_stats.csv",
    "derived/ui/calendar_day_index.csv",
]


@dataclass
class _AppState:
    """Mutable app state for the local server.

    The server is typically started for a specific run directory. Upload support
    creates additional run directories and switches the active run in-memory so
    the UI can browse the newly analyzed dataset without restarting.
    """

    run_dir: Path
    uploads_root: Path


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
    state = _AppState(run_dir=run_dir, uploads_root=run_dir.parent / "uploaded")

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/") or "/"
        if path.startswith("/api/"):
            status, headers, body = handle_api(state=state, path=path, environ=environ)
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


def handle_api(*, state: _AppState, path: str, environ) -> tuple[str, list[tuple[str, str]], bytes]:
    """Handle `/api/*` routes."""
    run_dir = state.run_dir
    presence, missing = _artifact_presence(run_dir)
    method = (environ.get("REQUEST_METHOD") or "GET").upper()

    if path == "/api/run":
        payload = {
            "run_dir": str(run_dir),
            "run_id": run_dir.name,
            "required_files": list(_REQUIRED_UI_FILES),
            "artifacts_present": presence,
            "missing_files": missing,
            "default_metric": "check_message_count",
            "available_metrics": ["check_message_count", "check_event_count"],
            "can_upload": True,
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

    if path == "/api/upload":
        if method != "POST":
            return json_response({"error": "method_not_allowed"}, status="405 Method Not Allowed")
        try:
            result = handle_upload(state=state, environ=environ)
        except ValueError as exc:
            return json_response({"error": "bad_request", "message": str(exc)}, status="400 Bad Request")
        except Exception as exc:  # pragma: no cover - defensive
            return json_response({"error": "upload_failed", "message": str(exc)}, status="500 Internal Server Error")
        return json_response(result)

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
    if path == "/api/top-lines":
        return json_response(artifacts.get_top_lines())

    return json_response({"error": "not_found"}, status="404 Not Found")


def handle_upload(*, state: _AppState, environ) -> Dict[str, object]:
    """Accept an uploaded export, run analysis, and switch the active run.

    The request body is streamed verbatim to disk (JSON array/object, or NDJSON).
    The analyzer (`analyze_export`) uses streaming parsing and supports both JSON
    and NDJSON variants.
    """
    run_dir = state.run_dir
    uploads_root = state.uploads_root
    uploads_root.mkdir(parents=True, exist_ok=True)

    new_run_dir = _allocate_uploaded_run_dir(uploads_root)
    raw_dir = new_run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / "upload.json"

    bytes_written = _stream_request_body_to_file(environ=environ, out_path=upload_path)
    if bytes_written <= 0:
        raise ValueError("empty upload")

    analyze_export(upload_path, new_run_dir, tg_checkstats_argv=["tg-checkstats", "serve", "--upload"])

    # Only switch after successful analysis.
    state.run_dir = new_run_dir

    presence, missing = _artifact_presence(new_run_dir)
    return {
        "run_dir": str(new_run_dir),
        "run_id": new_run_dir.name,
        "bytes_written": bytes_written,
        "artifacts_present": presence,
        "missing_files": missing,
    }


def _allocate_uploaded_run_dir(uploads_root: Path) -> Path:
    """Create and return a unique uploaded run directory path."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    for i in range(1000):
        suffix = "" if i == 0 else f"-{i}"
        candidate = uploads_root / f"{stamp}{suffix}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("failed to allocate uploaded run directory (too many collisions)")


def _stream_request_body_to_file(*, environ, out_path: Path, chunk_size: int = 1024 * 64) -> int:
    """Stream the WSGI request body to `out_path` and return bytes written."""
    stream = environ.get("wsgi.input")
    if stream is None:
        raise ValueError("missing request body stream")

    length_raw = environ.get("CONTENT_LENGTH")
    length: int | None = None
    if isinstance(length_raw, str) and length_raw.strip():
        try:
            length = int(length_raw)
        except ValueError:
            length = None

    written = 0
    with out_path.open("wb") as handle:
        if length is None:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
        else:
            remaining = length
            while remaining > 0:
                chunk = stream.read(min(chunk_size, remaining))
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                remaining -= len(chunk)

    return written


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
