---
# bezum-analysator-i6la
title: Refactor histogram UI PRD to v1.1 structure + data contract
status: completed
type: task
priority: normal
created_at: 2026-02-04T15:56:15Z
updated_at: 2026-02-04T15:58:24Z
---

Incorporate hard-nosed critique into the histogram web UI PRD:
- Use week_start_date as the primary week key
- Lock normalization denominators
- Specify minimal derived artifact set + CSV schemas + dense/sparse rules
- Clarify metric definitions (message vs event) and avoid frontend recomputation
- Strengthen acceptance criteria with invariants

## Checklist
- [x] Update PRD to v1.1 structure and decisions
- [x] Ensure artifact paths align with run layout
- [x] Commit PRD + bean file
- [x] Mark bean completed
