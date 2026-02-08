# Analyse der Beförderungsentgeltzahlungsumgehungsmaßnahmen in Leipzig 🚋📊

A small CLI + web dashboard that helps you turn raw Telegram chatter into useful check-pattern insights:

1. download a Telegram chat/channel history (via `telegram-download-chat`)
2. detect “check events” in messages (e.g. *Kontrolle*, *Kontis*, “3k”, “3–5k”)
3. aggregate time-based stats (day / month / weekday / hour)
4. compute a Bayesian posterior probability of “a check happening on a day”

The intended use-case is transit “ticket inspection” reports (German: *Kontrolle*)
posted into a Telegram channel/group (example chat: `https://t.me/freifahren_leipzig`),
but you can point it at any chat whose messages contain your signal words. Think of it as: collect, detect, aggregate, visualize.

---

## Quickstart 🚀

### 0) Requirements ✅

- Python 3.10+
- A Telegram account (for exporting via API)

This repo intentionally **does not** bundle the exporter. Exporting is delegated to
the external CLI `telegram-download-chat`.

### 1) Install 🛠️

Using `uv` (recommended):

```bash
uv venv
uv pip install -e ".[dev]"

# exporter (separate tool)
uv pip install telegram-download-chat
```

Or with pip:

```bash
python -m venv .venv
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pip install telegram-download-chat
```

### 2) Configure Telegram API credentials (api_id + api_hash) 🔐

`telegram-download-chat` uses Telegram’s MTProto API. To use it you need an **API ID**
and **API hash** linked to your Telegram account.

1. Go to `https://my.telegram.org`
2. Sign in with your Telegram phone number
3. Open **API development tools**
4. Create an application (any name/URL is fine for personal use)
5. Copy:
   - `api_id` (a number)
   - `api_hash` (a hex-ish string)

Create a `.env` file in the repo root:

```bash
cat > .env <<'EOF'
API_ID=123456
API_HASH=0123456789abcdef0123456789abcdef
EOF
```

Notes:
- Secrets are loaded automatically (the CLI calls `python-dotenv`).
- The exporter config is written to a **temporary file** and deleted after the export.
- Don’t commit `.env`. Treat `API_HASH` like a password.

### 3) Export + analyze 📥➡️📈

Run everything end-to-end into a “run directory”:

```bash
uv run tg-checkstats run \
  --chat https://t.me/freifahren_leipzig \
  --out runs/freifahren_leipzig
```

Or run steps separately:

```bash
# export -> runs/<run>/raw/export.json
uv run tg-checkstats export --chat https://t.me/freifahren_leipzig --out runs/freifahren_leipzig

# analyze -> runs/<run>/derived/*.csv + runs/<run>/run_metadata.json
uv run tg-checkstats analyze --input runs/freifahren_leipzig/raw/export.json --out runs/freifahren_leipzig
```

### 4) Open the dashboard (local) 🌐

```bash
uv run tg-checkstats serve --run runs/freifahren_leipzig --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

---

## Downloading chats from Telegram channels (how it works) 📡

This project does not scrape Telegram directly; it shells out to:

- `telegram-download-chat <chat> --output <path>`

`tg-checkstats export` / `tg-checkstats run` will:

- look for `API_ID`/`API_HASH` (or `api_id`/`api_hash`) in the environment
- write a temporary YAML config file for `telegram-download-chat`
- call `telegram-download-chat` with `--config <temp.yml>`
- delete the temp config file afterwards

Example:

```bash
API_ID=123456 API_HASH=... uv run tg-checkstats export \
  --chat https://t.me/freifahren_leipzig \
  --out runs/freifahren_leipzig
```

About authentication:
- On first use, `telegram-download-chat` typically prompts you to log in (phone + code).
  Run the export in a real terminal session (TTY), not a background job.
- You must have access to the chat (public, or joined if private).

Already have an export? Nice.
- If you already have a JSON export (array/object/NDJSON), skip export and run `tg-checkstats analyze`.
- The deployed web UI also supports uploading exports via `POST /api/upload`.

---

## Analysis: what gets extracted (and how) 🔎

### Inputs supported 📂

The analyzer streams the export file (no need to load everything into RAM) and supports:

- a JSON array of messages: `[ { ... }, { ... } ]`
- a JSON object with a `messages` array: `{ "messages": [ ... ] }`
- NDJSON (one JSON object per line)

Timestamps are parsed from ISO strings or epoch seconds and normalized to UTC, then
bucketed in the **Europe/Berlin** timezone for “day/week/month” calculations.

### Message filtering 🧹

Each message is:

- de-duplicated by message ID
- skipped if it has no timestamp
- optionally filtered by:
  - service messages (join/leave/etc.)
  - bot messages
  - forwarded messages

(See `tg-checkstats analyze --help` for flags.)

### Event detection (“check events”) 🎯

Detection is deterministic and regex-based. The current detector looks for:

- **k-tokens**: `3k`, `4 K`, `3-5k`, `4/5k` (with guards to avoid false matches like `2k€`)
- **control keywords** and inflections: `Kontrolle`, `Kontis`, `Kontrolleure`, `Kontrollettis`, …
- **transit context** (line/direction/location), used both as extra metadata and as a weaker signal

When an event is detected, the analyzer writes an `events.csv` row with extracted fields like:

- `k_min`, `k_max`, `k_qualifier` (exact/range/approx/multiple/unknown)
- `control_keyword_forms` (surface forms matched)
- `line_id`, `mode_guess` (tram/bus), `direction_text`, `location_text`, `platform_text`
- `confidence_score` (a small additive score derived from the signals above)

### Stitching follow-ups (optional) 🧵

In real chats, “details” sometimes arrive as follow-up messages (e.g. line + direction in a second message).
When enabled (default), the analyzer will stitch “detail-only” messages from the **same sender**
into the previous event if they arrive within a small time window (default: 5 minutes).

### Outputs written 🗂️

Given `--out runs/<run>`, outputs land in:

- `runs/<run>/raw/export.json` (exported input, if you used `export`/`run`)
- `runs/<run>/derived/events.csv` (event-level rows)
- `runs/<run>/derived/*_counts.csv` (aggregations by day/month/weekday/hour/ISO-week/etc.)
- `runs/<run>/derived/ui/*` (CSV artifacts consumed by the dashboard)
- `runs/<run>/run_metadata.json` (config, versions, counts, dataset range, etc.)

---

## Bayesian probabilities (posterior “check chance”) 🧠

The dashboard shows a **posterior probability** of “a check happening on a day”, so you get more than just raw counts.

Model:
- Each **day** is treated as a Bernoulli trial.
- `success = 1` if that day has `check_event_count > 0`, otherwise `0`.

Prior:
- A **Beta prior** is used for the Bernoulli probability `p`.
- Default is **Jeffreys prior**: `Beta(α=0.5, β=0.5)` (uninformative and symmetric).

Posterior (conjugate update):
- After observing `n` days with `s` “success” days:
  - `p | data ~ Beta(α + s, β + (n - s))`

Displayed values:
- posterior mean: `(α + s) / (α + β + n)`
- a central 95% credible interval:
  - exact Beta quantiles if SciPy is installed
  - otherwise a clamped normal approximation (with a one-time warning in logs)

The UI computes these posteriors per:
- month (YYYY-MM)
- month × weekday (so you can compare e.g. “Mondays in February”)

---

## Deploying the web UI ☁️

### Render (blueprint) 🧩

This repo ships a `render.yaml` blueprint that deploys the web UI as a Render Web Service.
The deployed UI supports uploading Telegram exports (`/api/upload`) and analyzes them server-side.

1. Push this repo to GitHub.
2. In Render: **New** → **Blueprint** → select the repo.
3. Create the service.

Under the hood:
- Build: installs `requirements-render.txt` and installs the package (`pip install -e . --no-deps`)
- Start: `gunicorn tg_checkstats.wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`

### Configure storage (`TG_CHECKSTATS_RUN_DIR`) 💾

The web service needs a writable directory for uploads + derived artifacts:

- `TG_CHECKSTATS_RUN_DIR=/tmp/tg-checkstats/run/current` (default)

Uploads are analyzed into sibling directories under:

- `<TG_CHECKSTATS_RUN_DIR>/../uploaded/`

On Render’s Free plan, the filesystem is ephemeral: uploads vanish when the service restarts/spins down.
For persistence, use a paid plan + persistent disk and set `TG_CHECKSTATS_RUN_DIR` under the disk mount
(for example: `/var/data/tg-checkstats/run/current`).

### Deploy elsewhere 🐳

Any PaaS/container environment that can run a WSGI app works:

```bash
gunicorn tg_checkstats.wsgi:app --bind 0.0.0.0:$PORT
```

---

## Helper script (optional) ⚙️

There is also a small wrapper script that:

1. creates a timestamped run directory
2. downloads the export (with an optional limit)
3. runs analysis

```bash
./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig
```

Common overrides:

```bash
# Stable run directory naming
RUNS_DIR=runs RUN_ID=full_export_1 ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig

# Explicit run directory name
RUN_NAME=freifahren_full ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig

# Limit download (0 = no limit)
EXPORT_LIMIT=5000 ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig
```

Note: this script calls `telegram-download-chat` directly and does not generate a temp config from `.env`.
If you need `API_ID`/`API_HASH` handling, prefer `tg-checkstats export` / `tg-checkstats run`.

---

## Troubleshooting 🩺

- Export fails immediately: check that `telegram-download-chat` is installed and on your `PATH`.
- Missing UI artifacts: run `tg-checkstats analyze` for the run directory you’re serving.
- SciPy missing in production: credible intervals fall back to a normal approximation (mean stays exact).
- Privacy: Telegram exports contain message content + metadata. Treat `runs/` as sensitive data.

---

## Development 👩‍💻

```bash
uv run pytest
```

## License 📄

GNU GPL (see `LICENSE`).
