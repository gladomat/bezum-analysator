# PRD — Web UI: Monthly histograms → weekly drilldown + daily averages

**Status:** Draft  
**Owner:** You  
**Target:** Local web UI for tg-checkstats run outputs (no hosted service required)

---

## 0) Summary

Add a local website for exploring tg-checkstats results with an interactive drilldown:

1. **Month overview:** a histogram/bar chart for each month in the dataset.
2. **Month detail:** clicking a month shows a **week grid** (rows = weeks, columns = Mon..Sun). Clicking a week drills into that week.
3. **Week detail:** show **per-day histograms by hour-of-day** (7 panels for Mon..Sun).
4. **Month averages:** show the **average per weekday** for the selected month (Mon..Sun).

The UI should work against a single run directory and read precomputed derived artifacts, so it remains fast and reproducible.

---

## 1) Context & problem

tg-checkstats currently emits audit-friendly CSV outputs (events + aggregates). This is great for pandas/Excel, but it is slow and cumbersome for rapid exploration. You want a lightweight, local “exploration UI” to spot seasonality patterns and then drill down into a specific month/week/day quickly.

---

## 2) Goals / Non-goals

### Goals

- G1 — **Fast exploration**: Open a run and see monthly patterns immediately.
- G2 — **Low friction**: No external DB; no hosted infra; usable offline.
- G3 — **Drilldown**: Month → week → day-level histograms with one click.
- G4 — **Consistency with CLI outputs**: UI is derived from deterministic artifacts.

### Non-goals (this step)

- User auth, multi-user sharing, or hosting
- Editing detection rules or re-running analysis from the UI
- Arbitrary cross-run comparisons (can be a follow-up)

---

## 3) Users & primary use cases

Primary user: you (local operator).

Use cases:

1. **Monthly scan**: Identify “hot” months quickly (total and/or normalized rate).
2. **Month drilldown**: Identify which week(s) in that month drive the month pattern.
3. **Weekly drilldown**: See which day(s) and time distribution (histograms) drive a week.
4. **Month averages**: Compare weekday means within the month to understand weekday bias.

---

## 4) Definitions (metrics + time)

**Timezone:** Europe/Berlin (consistent with analyzer outputs).

**Event vs message counts:**

- `check_message_count`: number of matched messages (each matched message counts as 1).
- `check_event_count`: weighted count (depends on `event_count_policy`; often equals message count, but can differ).

**Default display metric:** `check_event_count` (with a UI toggle to show `check_message_count`).

---

## 5) UX overview

### 5.1 Entry: select a run

The UI needs a way to select which analysis run to display. Options:

- A) Start the server with `--run <path>` (recommended for v1).
- B) A file picker within the UI (nice-to-have; depends on framework).

### 5.2 Page: Month overview

**Primary chart:** bar chart with one bar per month label `YYYY-MM` in the dataset.

**Controls:**

- Metric toggle: `check_event_count` vs `check_message_count`
- Y-axis toggle: `total` vs `per-day normalized` (where available)
- Filter: date range (optional for v1; can be added later)

**Interaction:**

- Clicking a month opens Month detail for that `YYYY-MM`.

### 5.3 Page: Month detail (week list + averages)

**Week grid (required):**

- Show a plot with **one row per week** in/overlapping the selected month, laid out **Mon..Sun**.
- Each cell represents one calendar day; the cell value is that day's total for the selected metric.
- Days outside the selected month are shown but visually de-emphasized (e.g., greyed) and excluded from month totals/means.

**Interaction:**

- Clicking a week (row label or any in-month cell in that row) navigates to Week detail for that ISO week.

**Averages panel (required):**

- Bar chart of **mean events per weekday** within the selected month: Mon..Sun.
- If the month contains a weekday only 4 times (or partial month), the mean uses occurrences in-range.

### 5.4 Page: Week detail (per-day histograms by hour-of-day)

After selecting a week, show 7 small histograms (one per weekday, Mon..Sun) for that week.

**Histogram spec (required):**

- X-axis: hour-of-day (0–23)
- Y-axis: count for selected metric (`check_event_count` or `check_message_count`)

**Day panels:**

- Title: `YYYY-MM-DD (Mon)` etc.
- Subtitle: total count for that day
- Empty days: render as all zeros (for consistent comparison)

---

## 6) Data requirements

### 6.1 Inputs the UI reads (current outputs)

From `<run>/derived/`:

- `month_counts_normalized.csv`: month totals + days in range + per-day rates
- `daily_counts.csv`: daily totals (zero-filled across dataset range)
- `events.csv`: full matched events (may be large)

### 6.2 Additional derived outputs (recommended for v1 UI performance)

To avoid requiring the UI to parse a large `events.csv`, add one or both of:

1. `date_hour_counts.csv`
   - Columns: `date_berlin`, `hour`, `check_message_count`, `check_event_count`
   - Zero-filled per day-hour across dataset range (or only for days with any events + UI fills zeros).

2. `month_weekday_counts.csv`
   - Columns: `month`, `weekday_idx`, `weekday`, `weekday_occurrences_in_month`, `mean_messages_per_weekday_in_month`, `mean_events_per_weekday_in_month`, plus totals.

These keep the UI deterministic while making it fast and memory-safe.

---

## 7) Functional requirements

### FR1 — Month overview histogram

- The UI shall render one bar per `YYYY-MM` month in the dataset.
- The UI shall support toggling between:
  - total counts per month
  - normalized per-day rates per month (if the source provides `days_in_month_in_range`)

### FR2 — Month selection

- Clicking a month shall navigate to a Month detail view for that month.
- The Month detail view shall show which days are considered “in-range” for the month (especially for partial first/last months).

### FR3 — Month averages by weekday

- The Month detail view shall show mean per weekday (Mon..Sun) for the selected month.
- Means shall be computed as `total_count_for_weekday_in_month / weekday_occurrences_in_month`.
- The UI shall label partial months/weeks clearly (e.g., “partial month” flag).

### FR4 — Weekly drilldown

- The Month detail view shall render a week grid (rows = weeks, columns = Mon..Sun) for the selected month.
- Each day cell shall show the day's total for the selected metric.
- Clicking a week shall navigate to Week detail for that ISO week.
- Day cells outside the selected month shall be visually indicated and excluded from month-level aggregates and means.

### FR5 — Per-day histogram (hour-of-day)

- For each day in the selected week (Mon..Sun), the UI shall show a histogram across hours 0–23.
- The UI shall support the metric toggle for the histogram values.

### FR6 — Shareable state (nice-to-have for v1)

- URL state should encode selection: run (or run id), month, week, and metric, so views can be bookmarked locally.

---

## 7.1 API / data access (v1 shape)

If a local server is used (recommended), keep the API minimal and read-only:

- `GET /api/run` → `{ run_metadata, available_artifacts }`
- `GET /api/months` → month series for Month overview (pre-joined for total + normalized)
- `GET /api/month/{yyyy_mm}` → month detail payload (weekday means + weeks overlapping month)
- `GET /api/week/{iso_year}/{iso_week}` → per-day histogram payload for the week (7 days × 24 hours)

Notes:

- Prefer returning “chart-ready” JSON to keep frontend logic small.
- Missing artifacts should return a clear error indicating the required derived CSV(s).

---

## 8) Non-functional requirements

- NFR1 — **Local-first**: no external network dependency.
- NFR2 — **Performance**: Month overview should render in <1s for typical runs; week drilldown <1s after selecting a week.
- NFR3 — **Robustness**: If files are missing or malformed, show a clear error and which artifact is needed.
- NFR4 — **Determinism**: UI should only read derived artifacts; no “hidden recalculation” against raw exports unless explicitly initiated.

---

## 9) Acceptance criteria (definition of done)

- AC1: Given a run directory, Month overview renders bars for all months present in the run’s derived data.
- AC2: Clicking a month opens Month detail for that month.
- AC3: Month detail shows a week grid with rows=weeks and columns=Mon..Sun, with outside-month days visually indicated.
- AC4: Month detail displays averages per weekday (Mon..Sun) for that month.
- AC5: Clicking a week in the grid opens Week detail for that week.
- AC6: Week detail displays 7 per-day (Mon..Sun) hour-of-day histograms (0–23).
- AC7: Metric toggle updates all charts consistently.
- AC8: Partial month/week handling is visible and does not miscount days in range.

---

## 10) Decisions & open questions

**Decisions captured:**

- Drilldown histogram meaning: **hour-of-day (0–23)**.
- Month detail week grid: **rows=weeks, columns=Mon..Sun**, with outside-month days shown but visually de-emphasized.

Open question Q1: For Month overview bars, should the default Y value be:

- A) total per month
- B) normalized per day in that month (events/day)

---

## 11) Recommended approach (implementation shape)

**Recommendation:** A small local server + static SPA.

- Python entrypoint (future): `tg-checkstats serve --run <run-dir>`
- Server responsibilities: serve static assets + expose derived data as JSON
- Frontend: single-page app with Plotly (or similar) for interactive charts

This keeps the UI easy to run (`one command`) while avoiding heavyweight infrastructure.
