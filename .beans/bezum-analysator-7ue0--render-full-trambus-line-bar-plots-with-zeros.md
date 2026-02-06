---
# bezum-analysator-7ue0
title: Render full tram/bus line bar plots with zeros
status: completed
type: feature
priority: normal
created_at: 2026-02-06T14:09:31Z
updated_at: 2026-02-06T14:12:38Z
---

Replace the current line list statistic with two stacked bar plots (tram and bus) sorted highest-to-lowest left-to-right, including zero-count bars for lines with no detected checks.

## Checklist
- [x] Add failing tests for API payload including zero-count lines
- [x] Update backend line aggregation to include full line universe and zeros
- [x] Replace UI line list with stacked bar plots for tram and bus
- [x] Run targeted tests and full suite
- [x] Commit changes with bean updates
