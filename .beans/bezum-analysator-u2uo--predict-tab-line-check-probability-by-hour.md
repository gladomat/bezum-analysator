---
# bezum-analysator-u2uo
title: 'Predict tab: line check probability by hour'
status: in-progress
type: feature
created_at: 2026-02-06T14:44:51Z
updated_at: 2026-02-06T14:44:51Z
---

Add a new Predict tab that lets the user pick a tram/bus line and shows, for the current weekday, the posterior probability of >=1 detected check per hour (0-23) across all run data. Render as 24-bar chart with 95% CI whiskers and highlight current hour.

## Checklist
- [x] Add failing backend tests for predictor payload (24 hours, CI fields, current hour)
- [x] Implement UiArtifacts predictor aggregation (line x weekday x hour posterior)
- [x] Add /api/predict endpoint
- [x] Add UI route + controls + bar+whisker chart
- [x] Run targeted + full tests
- [x] Commit changes and close bean
