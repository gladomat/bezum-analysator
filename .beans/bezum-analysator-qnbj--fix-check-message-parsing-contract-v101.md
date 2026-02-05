---
# bezum-analysator-qnbj
title: Fix check-message parsing contract (v1.0.1)
status: completed
type: bug
priority: normal
created_at: 2026-02-05T14:19:20Z
updated_at: 2026-02-05T14:33:28Z
---

Parser mis-detects or mis-classifies real-world check messages.

Goal: Upgrade detection + extraction to handle K-count ranges, control keywords, validated line universe, direction/location/platform extraction, and short-window stitching of follow-up messages.

Defaults (unless user overrides):
- line+direction alone does NOT count as check
- hostile slang is NOT a trigger
- extract platform/Steig/Gleis separately

## Checklist
- [x] Reproduce current mis-parses with fixtures
- [x] Implement improved detection scoring
- [x] Implement K-count + keyword extraction
- [x] Implement line validation + mode guess
- [x] Implement direction/location/platform extraction
- [x] Add 5-min stitching for follow-ups
- [x] Add/adjust tests and run test suite
