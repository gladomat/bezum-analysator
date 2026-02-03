---
# tg-checkstats-cg5d
title: Fix tg-checkstats immutability + metadata
status: completed
type: bug
priority: normal
created_at: 2026-02-03T23:30:55Z
updated_at: 2026-02-03T23:35:33Z
---

Fix issues found during code review:

- Raw export can be overwritten; enforce immutability by default.
- run_metadata timestamps and sha256 should be correct and scalable.
- Add NDJSON parsing fallback.
- Ensure packaging has README.md.

## Checklist
- [x] Add failing tests for raw immutability in CLI
- [x] Add failing tests for metadata timestamps + sha256
- [x] Add failing test for NDJSON input
- [x] Implement CLI raw immutability + --force semantics
- [x] Implement streaming sha256 + correct timestamps in metadata
- [x] Implement NDJSON fallback parsing
- [x] Add README.md or adjust pyproject readme
- [x] Run full test suite
- [x] Commit changes including bean file
