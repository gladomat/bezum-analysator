# tg-checkstats

Local, headless CLI to export a public Telegram chat (via `telegram-download-chat`) and analyze "k-check" seasonality.

## Usage

```bash
tg-checkstats export --chat <chat> --out <run-dir>
tg-checkstats analyze --input <run-dir>/raw/export.json --out <run-dir>
tg-checkstats run --chat <chat> --out <run-dir>
tg-checkstats serve --run <run-dir>
```

## uv (recommended)

This repo is `uv`-friendly; install once, then run commands via `uv run`:

```bash
uv venv
uv pip install -e ".[dev]"

# analyze without re-downloading (uses existing raw export)
uv run tg-checkstats analyze --input runs/<run>/raw/export.json --out runs/<run> --force

# start the local Web UI
uv run tg-checkstats serve --run runs/<run> --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

## Helper Script

This repo includes a small wrapper script that creates a timestamped run directory,
downloads the export, then runs analysis:

```bash
./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig
```

Common overrides:

```bash
# Download everything (0 = no limit)
EXPORT_LIMIT=0 ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig

# Stable run directory naming
RUNS_DIR=runs RUN_ID=full_export_1 ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig

# Explicit run directory name
RUN_NAME=freifahren_full ./scripts/tg_checkstats_run.sh https://t.me/freifahren_leipzig
```

## Deploy to Render (Web UI)

This repo ships a `render.yaml` blueprint that deploys the Web UI as a Render Web Service.
The deployed UI supports uploading Telegram exports (`/api/upload`) and will analyze them
server-side.

### Option A: Blueprint (recommended)

1. Push this repo to GitHub.
2. In Render: **New** → **Blueprint** → select the repo.
3. Create the service.

The service uses:
- Build: installs `requirements-render.txt` and installs the package (`pip install -e . --no-deps`)
- Start: `gunicorn tg_checkstats.wsgi:app --bind 0.0.0.0:$PORT ...`

On the Free plan, the service starts with an empty run directory; you’ll see a “No Data Artifacts Found” screen until you upload an export.

### Data persistence (uploads)

Uploaded exports + derived artifacts are written under the `TG_CHECKSTATS_RUN_DIR` parent directory.
On Render's Free plan the filesystem is ephemeral, so uploads will be lost when the service restarts / spins down.
The blueprint defaults to:

- `TG_CHECKSTATS_RUN_DIR=/tmp/tg-checkstats/run/current`

If you want persistence, use a paid plan and attach a persistent disk, then point `TG_CHECKSTATS_RUN_DIR` at a path under the disk mount (for example: `/var/data/tg-checkstats/run/current`).
