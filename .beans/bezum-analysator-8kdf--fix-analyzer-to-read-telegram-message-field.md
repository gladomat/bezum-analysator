---
# bezum-analysator-8kdf
title: Fix analyzer to read telegram 'message' field
status: completed
type: bug
priority: normal
created_at: 2026-02-05T14:53:18Z
updated_at: 2026-02-05T14:54:15Z
---

Analysis can produce zero events because telegram exports store message text under the `message` key (not `text`).

Requirements:
- Treat `message` as text content for detection
- Keep existing `text`/`caption` handling
- Add unit test coverage

## Checklist
- [x] Add failing test for `message` key
- [x] Implement text extraction supporting `message`
- [x] Run test suite
- [x] Sanity-run analyze on sample export
