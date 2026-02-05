---
# bezum-analysator-hxjn
title: Treat validated line+direction as check event
status: completed
type: feature
priority: normal
created_at: 2026-02-05T14:40:54Z
updated_at: 2026-02-05T14:41:42Z
---

User decision: line + direction (without any K/kontrolle keyword) should count as a check event.

Requirements:
- A message with a validated line id AND a direction token should be classified as check
- Keep direction-only messages as stitchable follow-ups (not standalone check events)
- Ensure E-suffix lines like 11E/10E/73E validate via base line

## Checklist
- [x] Add failing tests for line+direction-only messages
- [x] Implement line validation for *E suffix lines
- [x] Adjust confidence scoring / match_type
- [x] Run test suite
