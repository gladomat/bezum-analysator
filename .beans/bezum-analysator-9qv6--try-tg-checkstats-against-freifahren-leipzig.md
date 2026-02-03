---
# bezum-analysator-9qv6
title: Try tg-checkstats against freifahren_leipzig
status: completed
type: task
priority: normal
created_at: 2026-02-03T23:41:17Z
updated_at: 2026-02-03T23:45:22Z
---

Attempt to run tg-checkstats export/analyze for https://t.me/freifahren_leipzig and report what happens (deps/auth issues, command line to use).

## Checklist
- [x] Check telegram-download-chat availability
- [x] Attempt export to /tmp run dir
- [x] Run analyze (blocked by export auth)
- [x] Summarize result and next steps
- [x] Commit bean updates

## Notes / Result

- `telegram-download-chat` was not installed initially.
- After installing it, attempting to export `https://t.me/freifahren_leipzig` failed because the default config at:
  `/home/sandboxuser/.local/share/telegram-download-chat/config.yml`
  contains placeholders (`YOUR_API_ID` / `YOUR_API_HASH`).
- Next step: set real `api_id` / `api_hash` in that config file (or provide them via environment variables), then rerun export.
