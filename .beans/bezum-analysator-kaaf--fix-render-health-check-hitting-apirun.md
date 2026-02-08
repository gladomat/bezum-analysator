---
# bezum-analysator-kaaf
title: Fix Render health check hitting /api/run
status: completed
type: bug
priority: normal
created_at: 2026-02-08T18:57:34Z
updated_at: 2026-02-08T18:59:33Z
---

Render health checks currently call `/api/run`, causing continuous traffic to a non-liveness endpoint and likely contributing to restarts.

## Checklist
- [x] Confirm current health check path and route behavior
- [x] Add lightweight health endpoint
- [x] Update Render config to use health endpoint
- [x] Add/adjust tests for health endpoint behavior
- [x] Run tests
- [x] Mark bean completed
