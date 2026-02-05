---
# bezum-analysator-o9g0
title: 'Month detail: probable check hours per weekday'
status: completed
type: feature
priority: normal
created_at: 2026-02-05T16:29:11Z
updated_at: 2026-02-05T16:31:29Z
---

Under Month Detail weekday means, show probable check start/end hours (percentile window) and visualize with a bar plot including standard deviation (in minutes).

Definition:
- Use hourly distribution from `derived/ui/day_hour_counts.csv` (Berlin-local)
- Use weights = check_event_count per hour
- Window = p10..p90 of weighted hour distribution
- Mean + SD from weighted hours; show as HH:00 and ±minutes

## Checklist
- [x] Add backend fields to month weekday_stats payload
- [x] Add UI bar plot rendering
- [x] Add tests for window/mean/sd calculations
- [x] Verify UI loads + run tests

Follow-up:
- [x] Clarify empty ranges when n=0
