# Upload Data + Analyze in UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let a user upload a raw Telegram export (`export.json` / NDJSON) in the local Web UI, run analysis server-side, and immediately browse the resulting charts.

**Architecture:** Extend the existing stdlib WSGI server with a `POST /api/upload` route that streams the uploaded bytes to a new run directory, runs `tg_checkstats.analyze.analyze_export()` to generate UI artifacts, then switches the server’s active `run_dir` to the newly created run. The SPA adds an upload control that calls the new endpoint and refreshes state via existing `/api/run` + `/api/months`.

**Tech Stack:** Python (stdlib `wsgiref`), `tg_checkstats.analyze`, static SPA (`web_assets/app.js` + `styles.css`).

---

### Task 1: Add failing tests for upload + run switching

**Files:**
- Create: `tests/test_web_server_upload.py`

**Step 1: Write the failing test**

```python
def test_upload_creates_new_run_and_switches_active_run(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_server_upload.py -v`

Expected: FAIL because `/api/upload` does not exist (404) or server doesn’t switch run.

---

### Task 2: Implement `POST /api/upload` in the WSGI server

**Files:**
- Modify: `src/tg_checkstats/web_server.py`

**Step 1: Implement minimal server changes**
- Add a mutable server state holding the active `run_dir`.
- Add `POST /api/upload`:
  - Stream request body to `runs/uploaded/<timestamp>/raw/upload.json`
  - Run `analyze_export(upload_path, new_run_dir, tg_checkstats_argv=[...])`
  - Switch active `run_dir` to `new_run_dir`
  - Return JSON with new run info.

**Step 2: Run tests**

Run: `pytest tests/test_web_server_upload.py -v`

Expected: PASS.

---

### Task 3: Add upload control to the SPA

**Files:**
- Modify: `src/tg_checkstats/web_assets/index.html`
- Modify: `src/tg_checkstats/web_assets/app.js`
- Modify: `src/tg_checkstats/web_assets/styles.css`

**Step 1: Add a button + hidden file input**
- Upload button in header (or sidebar).
- File picker accepts `.json` and `.ndjson`.

**Step 2: Implement upload flow**
- Read file as `ArrayBuffer` (or `text`) and `fetch("/api/upload", { method: "POST", body: ... })`.
- Show progress in meta pill; on success, refresh `state.run`, `state.months`, year options, then `render()`.

**Step 3: Quick manual check**

Run: `uv run tg-checkstats serve --run runs/<some-run> --host 127.0.0.1 --port 8000`

Expected: Uploading a new export updates the displayed charts without restarting the server.

---

### Task 4: Run full suite and commit

**Step 1: Run full tests**

Run: `pytest -q`

Expected: PASS.

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: upload new data and analyze in web UI"
```

