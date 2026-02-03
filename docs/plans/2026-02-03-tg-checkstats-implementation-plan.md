# tg-checkstats Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement tg-checkstats per PRD v1.2: export/analyze CLI, detection, aggregation, CSV outputs, metadata, and tests.

**Architecture:** Python CLI (click) with modules for export, parsing, detection, aggregation, and IO. Stream JSON using ijson, compute counters incrementally, and emit deterministic CSVs plus run_metadata.json.

**Tech Stack:** Python 3.10+, click, python-dotenv, ijson, python-dateutil, tzdata, backports.zoneinfo (for py<3.9), pytest, pandas (optional for CSV convenience). uv for venv and dependency install. requirements.txt for all deps.

### Task 1: Project scaffolding + dependencies

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `src/tg_checkstats/__init__.py`
- Create: `src/tg_checkstats/__main__.py`
- Create: `src/tg_checkstats/cli.py`
- Create: `tests/__init__.py`

**Step 1: Write the failing test**

```python
def test_cli_help_shows_commands(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output
    assert "analyze" in result.output
    assert "run" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::test_cli_help_shows_commands -v`
Expected: FAIL (ImportError / cli missing)

**Step 3: Write minimal implementation**

- `requirements.txt` with click, python-dotenv, ijson, python-dateutil, tzdata, backports.zoneinfo, pytest, pandas
- `pyproject.toml` minimal with project metadata and console script `tg-checkstats = tg_checkstats.cli:app`
- `src/tg_checkstats/cli.py` with click group + empty commands (export/analyze/run)
- `src/tg_checkstats/__main__.py` to call CLI

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::test_cli_help_shows_commands -v`
Expected: PASS

**Step 5: Commit**

```bash
git add requirements.txt pyproject.toml src/tg_checkstats/__init__.py src/tg_checkstats/__main__.py src/tg_checkstats/cli.py tests/__init__.py tests/test_cli.py
git commit -m "feat: scaffold cli and deps"
```

### Task 2: Detection rules (k-token + keywords)

**Files:**
- Create: `src/tg_checkstats/detector.py`
- Create: `tests/test_detector.py`

**Step 1: Write the failing test**

```python
@pytest.mark.parametrize(
    "text,expected",
    [
        ("2k", [2]),
        ("2 k", [2]),
        ("3K", [3]),
        ("3k.", [3]),
        ("20 k!", [20]),
        ("2k€", []),
        ("2k/m", []),
        ("2к", []),
        ("2K", []),
        ("abc2k", []),
    ],
)
def test_k_token_matches(text, expected):
    matches = find_k_tokens(text)
    assert matches == expected


def test_keyword_matches():
    text = "die Kontrollettis kamen"
    result = find_keywords(text)
    assert "Kontrollettis" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_detector.py -v`
Expected: FAIL (module missing)

**Step 3: Write minimal implementation**

- Implement regex per PRD:
  `(?<!\w)([1-9]|1[0-9]|20)\s*[kK](?=$|[\s\.,!?;:\)\]\}\'\"-])`
- Implement `find_k_tokens(text) -> list[int]` and `find_keywords(text) -> list[str]`
- Implement `detect_event(search_text) -> dict` returning match_type, matched lists, and k_token_hit_count

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_detector.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/detector.py tests/test_detector.py
git commit -m "feat: add detection rules"
```

### Task 3: Timestamp parsing + text normalization

**Files:**
- Create: `src/tg_checkstats/parse.py`
- Create: `tests/test_parse.py`

**Step 1: Write the failing test**

```python
def test_normalize_text_list():
    assert normalize_text(["a", {"text": "b"}, 5]) == "ab"


def test_parse_timestamp_iso():
    dt = parse_timestamp("2024-01-02T03:04:05Z")
    assert dt.tzinfo is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parse.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- `normalize_text` per PRD
- `parse_timestamp` supporting ISO w/ tz, naive ISO (assume UTC + flag), and epoch seconds

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_parse.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/parse.py tests/test_parse.py
git commit -m "feat: add text normalization and timestamp parsing"
```

### Task 4: Aggregation (zero-fill + iso week)

**Files:**
- Create: `src/tg_checkstats/aggregate.py`
- Create: `tests/test_aggregate.py`

**Step 1: Write the failing test**

```python
def test_zero_fill_weekday_hour():
    rows = build_weekday_hour_matrix([])
    assert len(rows) == 168


def test_iso_week_range():
    rows = build_iso_week_series(date(2024, 1, 1), date(2024, 1, 10))
    assert len(rows) >= 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_aggregate.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Build incremental counters for daily/weekday/hour/week-of-month/iso-week
- Build zero-filled matrices and normalized month rates

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_aggregate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/aggregate.py tests/test_aggregate.py
git commit -m "feat: add aggregation and zero-fill"
```

### Task 5: CSV + metadata outputs

**Files:**
- Create: `src/tg_checkstats/io.py`
- Create: `tests/test_io.py`

**Step 1: Write the failing test**

```python
def test_csv_writer_deterministic(tmp_path):
    rows = [{"a": 1, "b": 2}, {"a": 2, "b": 3}]
    path = tmp_path / "out.csv"
    write_csv(path, rows, ["a", "b"])
    assert path.read_text().splitlines()[0] == "a,b"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_io.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Implement deterministic CSV writer (UTF-8, \n, RFC4180 quoting)
- Implement metadata JSON writer with stable ordering

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_io.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/io.py tests/test_io.py
git commit -m "feat: add deterministic outputs"
```

### Task 6: Analyzer pipeline

**Files:**
- Create: `src/tg_checkstats/analyze.py`
- Create: `tests/test_analyze.py`

**Step 1: Write the failing test**

```python
def test_analyze_minimal(tmp_path, fixture_json):
    out = analyze_export(fixture_json, tmp_path)
    assert (tmp_path / "derived" / "events.csv").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyze.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Stream parse JSON export via ijson
- Normalize text + timestamps; compute event detection
- Track counters and emit CSVs + metadata

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyze.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/analyze.py tests/test_analyze.py
git commit -m "feat: add analyzer pipeline"
```

### Task 7: Export integration

**Files:**
- Create: `src/tg_checkstats/export.py`
- Create: `tests/test_export.py`

**Step 1: Write the failing test**

```python
def test_build_export_command():
    cmd = build_export_command("mychat", "/tmp/out.json", 3, 5)
    assert "telegram-download-chat" in cmd[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_export.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Build exporter command and run via subprocess
- Read env via dotenv, write temp config

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_export.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/export.py tests/test_export.py
git commit -m "feat: add export integration"
```

### Task 8: CLI wiring + end-to-end tests

**Files:**
- Modify: `src/tg_checkstats/cli.py`
- Create: `tests/test_cli_e2e.py`

**Step 1: Write the failing test**

```python
def test_analyze_command(tmp_path, fixture_json, runner):
    result = runner.invoke(cli, ["analyze", "--input", str(fixture_json), "--out", str(tmp_path)])
    assert result.exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_e2e.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Wire CLI to export/analyze pipeline
- Ensure `--force` behavior per PRD

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_e2e.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tg_checkstats/cli.py tests/test_cli_e2e.py
git commit -m "feat: wire cli commands"
```

### Task 9: Verification

**Files:**
- Modify: `.beans/bezum-analysator-f1fl--implement-tg-checkstats-cli.md`

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: PASS

**Step 2: Update bean checklist**

Mark all checklist items complete.

**Step 3: Commit**

```bash
git add .beans/bezum-analysator-f1fl--implement-tg-checkstats-cli.md
git commit -m "chore: complete bean for tg-checkstats"
```
