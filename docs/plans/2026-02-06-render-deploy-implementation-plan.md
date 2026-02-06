# Render Deployment (tg-checkstats) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make tg-checkstats deployable on Render as a Web Service using Gunicorn, with an env-configurable run directory for uploads.

**Architecture:** Add a small `tg_checkstats.wsgi` module exposing a WSGI callable constructed from `tg_checkstats.web_server.create_app`. Provide Render config (blueprint + optional Dockerfile) and a minimal production requirements file.

**Tech Stack:** Python, Gunicorn, WSGI (stdlib + existing app), Render Web Service.

### Task 1: Add Gunicorn WSGI entrypoint

**Files:**
- Create: `src/tg_checkstats/wsgi.py`

**Steps:**
1. Create `tg_checkstats.wsgi:app` using `TG_CHECKSTATS_RUN_DIR` (default to a writable path).
2. Ensure the run directory exists at startup (mkdir parents).

### Task 2: Add minimal production requirements

**Files:**
- Create: `requirements-render.txt`

**Steps:**
1. Include only runtime deps needed for UI + analysis + gunicorn.
2. Keep SciPy optional (UI works without it).

### Task 3: Add Render configuration

**Files:**
- Create: `render.yaml`
- Create: `.dockerignore`
- (Optional) Create: `Dockerfile`

**Steps:**
1. Configure a Render Web Service with `buildCommand` installing `requirements-render.txt` and the package.
2. Configure `startCommand` to run gunicorn bound to `$PORT`.
3. Set `TG_CHECKSTATS_RUN_DIR` and document persistent disk needs.

### Task 4: Update docs

**Files:**
- Modify: `README.md`

**Steps:**
1. Add “Deploy to Render” section with blueprint instructions and required env vars.
2. Mention persistent disk for uploaded data.

### Task 5: Verify + commit

**Steps:**
1. Run tests (and a quick local gunicorn smoke run).
2. Commit code + bean file updates.

