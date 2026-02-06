"""Web server upload endpoint tests.

These tests exercise the WSGI app directly (no real HTTP server) to ensure that:
- A new upload can be analyzed server-side.
- The server switches its active run directory to the newly created run.
"""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any, Callable

from tg_checkstats.analyze import analyze_export
from tg_checkstats.web_server import create_app


def _call_wsgi_app(
    app: Callable,
    *,
    method: str,
    path: str,
    body: bytes = b"",
    content_type: str = "",
    query_string: str = "",
) -> tuple[str, bytes]:
    """Call a WSGI app and return (status, body_bytes)."""
    headers: dict[str, str] = {}
    captured: dict[str, Any] = {}

    def start_response(status: str, hdrs: list[tuple[str, str]]) -> None:
        captured["status"] = status
        for k, v in hdrs:
            headers[k.lower()] = v

    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string or "",
        "wsgi.input": BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
    }
    if content_type:
        environ["CONTENT_TYPE"] = content_type

    chunks = app(environ, start_response)
    payload = b"".join(chunks)
    return captured.get("status", "000 Unknown"), payload


def test_upload_creates_new_run_and_switches_active_run(tmp_path: Path) -> None:
    """Uploading a new export analyzes it and changes the server's active run."""
    runs_dir = tmp_path / "runs"
    initial_run = runs_dir / "initial"
    initial_run.mkdir(parents=True, exist_ok=True)
    (initial_run / "raw").mkdir(parents=True, exist_ok=True)
    export_path = initial_run / "raw" / "export.json"
    export_path.write_text(
        json.dumps(
            [
                {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k"},
                {"id": 2, "date": "2024-01-02T08:00:00Z", "text": "nope"},
            ]
        ),
        encoding="utf-8",
    )
    analyze_export(export_path, initial_run)

    app = create_app(run_dir=initial_run)

    status, body = _call_wsgi_app(app, method="GET", path="/api/run")
    assert status.startswith("200")
    payload = json.loads(body.decode("utf-8"))
    assert payload["run_id"] == "initial"

    upload_bytes = json.dumps(
        [
            {"id": 1, "date": "2024-02-01T10:00:00Z", "text": "Kontis"},
            {"id": 2, "date": "2024-02-03T08:00:00Z", "text": "2k"},
        ]
    ).encode("utf-8")
    status, body = _call_wsgi_app(
        app,
        method="POST",
        path="/api/upload",
        body=upload_bytes,
        content_type="application/json",
    )

    # This should be green once the upload endpoint exists.
    assert status.startswith("200")
    upload_payload = json.loads(body.decode("utf-8"))
    assert "run_id" in upload_payload
    assert upload_payload["run_id"] != "initial"

    status, body = _call_wsgi_app(app, method="GET", path="/api/run")
    assert status.startswith("200")
    after = json.loads(body.decode("utf-8"))
    assert after["run_id"] == upload_payload["run_id"]


def test_top_lines_api_returns_tram_and_bus_rankings(tmp_path: Path) -> None:
    """`/api/top-lines` returns split rankings for tram and bus line checks."""
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    export_path = run_dir / "raw" / "export.json"
    export_path.write_text(
        json.dumps(
            [
                {"id": 1, "date": "2024-01-01T10:00:00Z", "text": "2k tram 10"},
                {"id": 2, "date": "2024-01-02T10:00:00Z", "text": "2k tram 10"},
                {"id": 3, "date": "2024-01-03T10:00:00Z", "text": "kontis bus 60"},
            ]
        ),
        encoding="utf-8",
    )
    analyze_export(export_path, run_dir)
    app = create_app(run_dir=run_dir)

    status, body = _call_wsgi_app(app, method="GET", path="/api/top-lines")
    assert status.startswith("200")
    payload = json.loads(body.decode("utf-8"))

    assert {"tram", "bus"}.issubset(payload.keys())
    assert payload["tram"][0]["line_id"] == "10"
    assert payload["tram"][0]["check_event_count"] == 2
    assert payload["bus"][0]["line_id"] == "60"
    assert payload["bus"][0]["check_event_count"] == 1
    tram_line_1 = next((row for row in payload["tram"] if row["line_id"] == "1"), None)
    assert tram_line_1 is not None
    assert tram_line_1["check_event_count"] == 0


def test_predict_api_returns_24_hours_and_posterior_fields(tmp_path: Path) -> None:
    """`/api/predict/line/<id>` returns 24-hour posterior rows."""
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    export_path = run_dir / "raw" / "export.json"
    export_path.write_text(
        json.dumps(
            [
                {"id": 1, "date": "2024-01-01T10:00:00+01:00", "text": "2k tram 10"},
                {"id": 2, "date": "2024-01-08T10:00:00+01:00", "text": "Kontis tram 10"},
                {"id": 3, "date": "2024-01-15T10:00:00+01:00", "text": "nope"},
            ]
        ),
        encoding="utf-8",
    )
    analyze_export(export_path, run_dir)
    app = create_app(run_dir=run_dir)

    status, body = _call_wsgi_app(
        app,
        method="GET",
        path="/api/predict/line/10",
        query_string="mode=tram&weekday=0",
    )
    assert status.startswith("200")
    payload = json.loads(body.decode("utf-8"))

    assert payload["line_id"] == "10"
    assert payload["mode"] == "tram"
    assert payload["weekday_idx"] == 0
    assert len(payload["hours"]) == 24
    row0 = payload["hours"][0]
    assert {"hour", "trials", "successes", "prob_mean", "prob_low", "prob_high"}.issubset(row0.keys())
