# PRD v1.1 — Web UI: Month overview → week grid → weekday/hour histograms

**Status:** Draft  
**Owner:** You  
**Target:** Local, read-only web UI for tg-checkstats run outputs

---

## 0) Summary

Build a local, read-only website to explore tg-checkstats results with a fast drilldown:

- **Month overview:** bar chart per month showing **(a)** total matched count and **(b)** normalized per-day-in-range rate.
- **Month detail:** calendar week grid (rows = weeks keyed by `week_start_date`, columns = Mon..Sun) + weekday means.
- **Week detail:** 7 histograms (Mon..Sun), each showing hour-of-day distribution (0–23).

The interactive UI must not scan `events.csv`. It should use only pre-aggregated artifacts.

---

## 1) Goals

- Instant exploration of seasonality patterns (month, weekday, hour-of-day).
- Deterministic and reproducible: render what the analyzer produced; no hidden recomputation.
- Offline and low-friction: one-command launch, no database, no hosted infra.

---

## 2) Non-goals (v1.1)

- Editing detection rules or re-running analysis from the UI.
- Cross-run comparisons (future).
- User authentication / multi-user hosting.

---

## 3) Primary user journeys

1. **Scan months:** spot high/low months by total and normalized rate.
2. **Diagnose a month:** identify which weeks/days drive it (week grid) + weekday bias (means).
3. **Diagnose a week:** inspect time-of-day profile per weekday (7×24).

---

## 4) Definitions

**Timezone:** taken from `<run_dir>/run_metadata.json` (`config.timezone`, defaulting to `Europe/Berlin`).

**Day boundary:** midnight–midnight in the run timezone.

**Week key (required):** `week_start_date` = timezone-local Monday date (YYYY-MM-DD).

**Metric (v1.1):**

- `check_message_count`: number of matched messages (one per matched message).
- `check_event_count`: weighted count, defined by `run_metadata.json` (`config.event_count_policy`).

**Active metric (UI):**

- Default: `check_message_count`
- Optional toggle: show `check_event_count` (only if present end-to-end in the UI artifacts)

---

## 5) Required derived artifacts (data contract)

**Canonical location:** `<run_dir>/derived/ui/`

Notes:

- These files are a **UI-specific, chart-ready contract**. The analyzer may still write audit-friendly artifacts under `<run_dir>/derived/` (e.g. `events.csv`, other rollups), but the UI must rely only on `<run_dir>/derived/ui/` plus `<run_dir>/run_metadata.json`.
- The UI must not compute calendar boundaries itself; calendar columns are part of the contract to avoid subtle DST / ISO week / month-edge bugs.

All schemas below are required for v1.1 UI. Files are read-only.

### A) `month_counts.csv`

Columns:

- `month` (YYYY-MM)
- `month_check_message_count` (int)
- `month_check_event_count` (int)
- `days_in_range` (int)
- `messages_per_day_in_range` (float)
- `events_per_day_in_range` (float)

Rules:

- `days_in_range` counts only the days of that month present in the dataset date range.
- `messages_per_day_in_range = month_check_message_count / days_in_range`
- `events_per_day_in_range = month_check_event_count / days_in_range`

### B) `day_counts.csv`

Columns:

- `date` (YYYY-MM-DD) — timezone-local date
- `check_message_count` (int)
- `check_event_count` (int)
- `month` (YYYY-MM)
- `weekday_idx` (0=Mon..6=Sun)
- `weekday` (Mon..Sun)
- `iso_year` (int)
- `iso_week` (int)
- `week_start_date` (YYYY-MM-DD)
- `week_of_month` (1..5)

Rules:

- Must be **dense**: includes every date in the dataset date range (missing dates are not allowed).

### C) `day_hour_counts.csv` (sparse allowed)

Columns:

- `date` (YYYY-MM-DD) — timezone-local date
- `hour` (0..23)
- `check_message_count` (int)
- `check_event_count` (int)

Rules:

- Sparse allowed: missing `(date, hour)` implies 0.

### D) `month_weekday_stats.csv`

Columns:

- `month` (YYYY-MM)
- `weekday_idx` (0..6), `weekday` (Mon..Sun)
- `weekday_occurrences_in_range` (int)
- `check_message_count` (int)
- `check_event_count` (int)
- `mean_messages_per_weekday_in_range` (float)
- `mean_events_per_weekday_in_range` (float)

### E) `calendar_day_index.csv` (recommended; optional if `day_counts.csv` is dense)

Columns:

- `date` (YYYY-MM-DD)
- `month` (YYYY-MM)
- `weekday_idx`, `weekday`
- `iso_year`, `iso_week`
- `week_start_date`
- `week_of_month`

Purpose:

- Prevents duplicating calendar logic in the frontend (reduces subtle bugs around week/month boundaries).

Optional:

- `events.csv` remains optional and should not be required for any charts.

---

## 6) UI pages & behaviors

### 6.0 UI baseline (stitch references)

Use the provided Stitch mockups and HTML as the visual and layout baseline:

- Overview: `docs/stitch/seasonality_overview_dashboard/screen.png` and `docs/stitch/seasonality_overview_dashboard/code.html`
- Month detail: `docs/stitch/month_detail_seasonality_view/screen.png` and `docs/stitch/month_detail_seasonality_view/code.html`
- Week detail: `docs/stitch/week_detail_hourly_analysis/screen.png` and `docs/stitch/week_detail_hourly_analysis/code.html`
- Error (missing artifacts): `docs/stitch/data_missing_error_state/screen.png` and `docs/stitch/data_missing_error_state/code.html`

Global UI conventions implied by the Stitch assets:

- App shell: left sidebar navigation + top header with breadcrumbs and run controls.
- Typography: Inter (via Google Fonts) + Material Symbols icon set.
- Design tokens (from Tailwind config in Stitch HTML): `primary=#197fe6`, light background `#f6f7f8`, dark background `#111921`, rounded cards (`rounded-xl`), subtle borders + shadows.

### 6.1 Month overview

- Chart A: `month_check_message_count` per `month` (default metric)
- Chart B: `messages_per_day_in_range` per `month`
- Clicking a month opens Month detail for `month=YYYY-MM`.

Stitch alignment (Overview page):

- Include the top header elements shown in the mockup:
  - breadcrumb `run_id / overview`
  - timezone badge (Europe/Berlin)
  - “data loaded” status indicator
  - “Change run” control
- The bar chart styling should follow the “Monthly Activity Totals” card treatment.
- Secondary “Daily Check Rate” panel can be driven by weekday means (run-level or selected range); if omitted in v1.1, keep space for it in layout.

### 6.2 Month detail

**Week grid (required):**

- Rows are `week_start_date` for weeks that overlap the selected month.
- Columns are Mon..Sun.
- Cell value = `check_message_count` for that date (default metric; can toggle to `check_event_count`).
- Dates outside the selected month are visually de-emphasized and excluded from month-level aggregates.

**Weekday means (required):**

- Render means from `month_weekday_stats.csv` for the selected month.

Stitch alignment (Month detail / seasonality view):

- Add a month picker control (prev/next month + label) and optional “Export” action (export can be out-of-scope for v1.1; keep button as disabled or hidden).
- Week grid should match the “Activity Heatmap” look:
  - columns labeled Mon..Sun
  - week labels at left (display ISO week number for readability; routing still uses `week_start_date`)
  - day tiles show day-of-month + count, and encode intensity by background shade
- Provide an “Insights” side panel layout (can start minimal in v1.1):
  - Total for month and average-per-day-in-range
  - Weekday Average bar chart (driven by `month_weekday_stats.csv`)
  - Optional: weekly volume mini-chart and “top busiest days” list (future / v1.2)

### 6.3 Week detail

- Route key: `/week/<week_start_date>` (YYYY-MM-DD).
- Show 7 panels (Mon..Sun). For each day:
  - Histogram X-axis: hour (0–23)
  - Histogram Y-axis: `check_message_count` (default metric; can toggle to `check_event_count`)
  - Missing hours are rendered as 0.
  - Title shows date + weekday + day total for active metric.

Stitch alignment (Week detail / hourly analysis):

- Use the card grid layout from the mockup: 7 day cards with titles, date subtitles, and compact histograms.
- Provide a “Normalize (scale to %)” toggle as a v1.1 nice-to-have:
  - Off: bars show absolute counts (default)
  - On: each day’s histogram is normalized to 0–100% (sum of bins or max-bin normalization must be defined during implementation)

### 6.4 Missing artifacts (error state)

If required UI artifacts are missing for the selected run directory, show an explicit “No Data Artifacts Found” screen, modeled after:

- `docs/stitch/data_missing_error_state/screen.png`

Behavior:

- List required filenames and whether each is present:
  - `run_metadata.json`
  - `derived/ui/month_counts.csv`
  - `derived/ui/day_counts.csv`
  - `derived/ui/day_hour_counts.csv`
  - `derived/ui/month_weekday_stats.csv`
  - `derived/ui/calendar_day_index.csv` (only if the implementation chooses to require it)
- Prefer “Change run” over “Upload CSV Files” (upload can be a future enhancement).

---

## 7) API (minimal, chart-ready)

- `GET /api/run` → run metadata + artifact presence + dataset date range
- `GET /api/months` → rows from `month_counts.csv`
- `GET /api/month/<YYYY-MM>` → `{ month, weeks: [week_start_date...], grid: day cells, weekday_stats }`
- `GET /api/week/<YYYY-MM-DD>` → `{ week_start_date, days: [{date, weekday, check_message_count, check_event_count, hours: [{hour, check_message_count, check_event_count} x24]}] }`

Error handling:

- Each endpoint returns a clear error for missing artifacts, including the exact filenames required for that view.

---

## 8) Non-functional requirements

- NFR1: Overview render should be sub-second after loading `month_counts.csv`.
- NFR2: Month/week drilldowns should be sub-second by reading pre-aggregated artifacts and returning pre-shaped JSON.
- NFR3: The UI must never parse `events.csv` for charts.
- NFR4: UI should follow the Stitch layout and styling baseline under `docs/stitch/*` (sidebar, header, card spacing, typography, primary color).

---

## 9) Acceptance criteria (invariant-based)

- AC1: Month overview renders all months with correct totals and rates.
- AC2: For any month, sum of day counts for in-month days equals the month total (for both metrics, if both are exposed).
- AC3: For any date, sum of its 24 hourly bins equals the day total (for both metrics, if both are exposed).
- AC4: Week grid uses `week_start_date` routing; weeks crossing month boundaries behave predictably.
- AC5: Week detail always shows 7 panels and 24 bins per panel (zero-filled).

---

## 10) Decisions captured

- Drilldown histograms are **hour-of-day (0–23)**.
- Month detail uses a week grid with **rows = `week_start_date`** and **columns Mon..Sun**.
- Month overview shows **both totals and per-day-in-range normalized**.

---

## 11) Recommended implementation shape (future)

- Python entrypoint: `tg-checkstats serve --run <run-dir>`
- Server: serves static assets + exposes the minimal JSON API above
- Frontend: SPA with a chart library (Plotly or similar)
