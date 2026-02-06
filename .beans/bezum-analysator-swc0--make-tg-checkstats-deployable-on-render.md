---
# bezum-analysator-swc0
title: Make tg-checkstats deployable on Render
status: completed
type: task
priority: normal
created_at: 2026-02-06T15:26:52Z
updated_at: 2026-02-06T15:31:56Z
---

Goal: Deploy the tg-checkstats Web UI as a Render Web Service (public URL), using a production WSGI server (gunicorn) and a writable run directory for uploads.

## Checklist
- [x] Confirm desired deploy mode (upload-only vs preloaded run)
- [x] Add WSGI entrypoint for gunicorn
- [x] Add minimal Render runtime requirements
- [x] Add Render blueprint and/or Dockerfile
- [x] Update README with Render deploy steps
- [x] Run tests / smoke run server
- [x] Commit changes (include bean files)

## Notes
- Defaulted to **upload-only** deployment: the web service starts without a preloaded run and expects uploads via the UI. A preloaded run can be supported by setting `TG_CHECKSTATS_RUN_DIR` to a directory containing UI artifacts.
