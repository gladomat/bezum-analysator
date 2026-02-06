# Render Deployment (tg-checkstats) — Design

**Goal:** Deploy the tg-checkstats Web UI to Render as a public Web Service that can accept uploads of Telegram exports, run analysis server-side, and serve the SPA + JSON API.

## Assumptions

- This deployment is for the **Web UI + upload** workflow (no automatic Telegram export running on Render).
- Data uploaded via the UI should survive restarts, so a **persistent disk** is recommended.
- The existing local server is a WSGI app (via `tg_checkstats.web_server.create_app`) and can be served in production using Gunicorn.

## Architecture

- **Runtime server:** Gunicorn serves a WSGI callable exposed from `tg_checkstats.wsgi`.
- **State / storage:** An env var `TG_CHECKSTATS_RUN_DIR` points to a writable “current run” directory. The upload handler writes uploaded exports and derived artifacts into a sibling `uploaded/` directory. With a Render persistent disk mounted, these files persist across deploys/restarts.
- **Traffic:** `GET /` serves the SPA. `/api/*` serves JSON endpoints and accepts `POST /api/upload`.

## Deployment model options

1) **Native Render Web Service (recommended):** Use a `render.yaml` blueprint with:
   - `pip` install from a minimal requirements file for production
   - `gunicorn` start command binding to `0.0.0.0:$PORT`
   - persistent disk mount (for uploads + derived artifacts)

2) **Docker-based Render service:** Use a `Dockerfile` so the same image can run locally and on Render, at the cost of a slightly longer build.

