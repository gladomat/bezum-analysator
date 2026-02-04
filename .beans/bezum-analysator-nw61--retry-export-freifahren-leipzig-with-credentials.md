---
# bezum-analysator-nw61
title: Retry export freifahren_leipzig with credentials
status: todo
type: task
priority: normal
created_at: 2026-02-04T14:22:13Z
updated_at: 2026-02-04T14:23:25Z
---

User reports api_id/api_hash added; re-run export+analyze for https://t.me/freifahren_leipzig (smoke test with small limit).

## Checklist
- [x] Run telegram-download-chat export (limit 10)
- [ ] Run tg-checkstats analyze on export
- [x] Summarize outcome
- [ ] Commit bean updates

## Outcome

Export still fails in this environment because `telegram-download-chat` is reading placeholder credentials from:

- `~/.local/share/telegram-download-chat/config.yml` (`api_id: YOUR_API_ID`, `api_hash: YOUR_API_HASH`)

So I cannot proceed to analyze until that config is updated (or credentials are provided via env vars).
