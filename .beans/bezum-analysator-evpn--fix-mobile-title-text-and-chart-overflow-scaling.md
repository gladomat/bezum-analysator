---
# bezum-analysator-evpn
title: Fix mobile title text and chart overflow scaling
status: completed
type: bug
priority: normal
created_at: 2026-02-08T12:01:15Z
updated_at: 2026-02-08T12:04:19Z
---

Ensure mobile header uses full analysis title and make overview/predict charts fit narrow screens without overflow by adjusting responsive sizing and bar thickness.

## Checklist
- [x] Locate title i18n usage and set mobile title to full analysis text
- [x] Inspect chart rendering code for fixed-width assumptions
- [x] Implement responsive chart sizing and thinner bars on mobile
- [x] Validate UI tests and commit