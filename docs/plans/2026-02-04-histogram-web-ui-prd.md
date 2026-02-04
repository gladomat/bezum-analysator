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

**Timezone:** Europe/Berlin (all dates and week boundaries computed in Berlin time).

**Day boundary:** midnight–midnight Berlin.

**Week key (required):** `week_start_date` = Berlin-local Monday date (YYYY-MM-DD).

**Metric (v1.1):**

- `count`: number of matched messages (one per message).

Optional (only if the analyzer guarantees it end-to-end):

- `event_count`: weighted count (must be explicitly defined by the analyzer’s `event_count_policy` and present in all UI artifacts).

---

## 5) Required derived artifacts (data contract)

**Canonical location:** `<run_dir>/derived/ui/`

All schemas below are required for v1.1 UI. Files are read-only.

### A) `month_counts.csv`

Columns:

- `month` (YYYY-MM)
- `month_total` (int)
- `days_in_range` (int)
- `rate_per_day_in_range` (float)

Rules:

- `days_in_range` counts only the days of that month present in the dataset date range.
- `rate_per_day_in_range = month_total / days_in_range`

### B) `day_counts.csv`

Columns:

- `date` (YYYY-MM-DD)
- `day_total` (int)
- `month` (YYYY-MM)
- `weekday_idx` (0=Mon..6=Sun)
- `weekday` (Mon..Sun)
- `iso_year` (int)
- `iso_week` (int)
- `week_start_date` (YYYY-MM-DD)
- `week_of_month` (1..5)

Rules:

- Dense vs sparse: either is acceptable, but it must be consistent:
  - Dense: includes every date in the dataset date range (missing implies zero is not used).
  - Sparse: includes only dates with non-zero totals (UI fills missing dates with 0 after loading a calendar index).

### C) `day_hour_counts.csv` (sparse allowed)

Columns:

- `date` (YYYY-MM-DD)
- `hour` (0..23)
- `count` (int)

Rules:

- Sparse allowed: missing `(date, hour)` implies 0.

### D) `month_weekday_stats.csv`

Columns:

- `month` (YYYY-MM)
- `weekday_idx` (0..6), `weekday` (Mon..Sun)
- `weekday_occurrences_in_range` (int)
- `total` (int)
- `mean_per_weekday_in_range` (float)

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

### 6.1 Month overview

- Chart A: `month_total` per `month`
- Chart B: `rate_per_day_in_range` per `month`
- Clicking a month opens Month detail for `month=YYYY-MM`.

### 6.2 Month detail

**Week grid (required):**

- Rows are `week_start_date` for weeks that overlap the selected month.
- Columns are Mon..Sun.
- Cell value = `day_total` for that date.
- Dates outside the selected month are visually de-emphasized and excluded from month-level aggregates.

**Weekday means (required):**

- Render means from `month_weekday_stats.csv` for the selected month.

### 6.3 Week detail

- Route key: `/week/<week_start_date>` (YYYY-MM-DD).
- Show 7 panels (Mon..Sun). For each day:
  - Histogram X-axis: hour (0–23)
  - Histogram Y-axis: `count`
  - Missing hours are rendered as 0.
  - Title shows date + weekday + `day_total`.

---

## 7) API (minimal, chart-ready)

- `GET /api/run` → run metadata + artifact presence + dataset date range
- `GET /api/months` → rows from `month_counts.csv`
- `GET /api/month/<YYYY-MM>` → `{ month, weeks: [week_start_date...], grid: day cells, weekday_stats }`
- `GET /api/week/<YYYY-MM-DD>` → `{ week_start_date, days: [{date, weekday, day_total, hours[24]}] }`

Error handling:

- Each endpoint returns a clear error for missing artifacts, including the exact filenames required for that view.

---

## 8) Non-functional requirements

- NFR1: Overview render should be sub-second after loading `month_counts.csv`.
- NFR2: Month/week drilldowns should be sub-second by reading pre-aggregated artifacts and returning pre-shaped JSON.
- NFR3: The UI must never parse `events.csv` for charts.

---

## 9) Acceptance criteria (invariant-based)

- AC1: Month overview renders all months with correct totals and rates.
- AC2: For any month, sum of `day_total` for in-month days equals `month_total`.
- AC3: For any date, sum of its 24 hourly bins equals `day_total`.
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
