---
# bezum-analysator-0wxn
title: Replace normal-approx Beta CI with exact quantiles + bucketed updater
status: completed
type: feature
priority: normal
created_at: 2026-02-05T22:16:51Z
updated_at: 2026-02-05T22:24:43Z
---

Goal: keep existing Beta-Binomial update logic; use exact Beta quantile credible
intervals when SciPy is available (with a warning-once fallback); add minimal
per-bucket posterior-as-prior updaters + summaries; add tests.

## Checklist
- [x] Locate current beta_posterior_summary and interval logic
- [x] Add SciPy import guard + exact quantile CI path
- [x] Add BetaPrior + update helpers (single + bucketed + summaries)
- [x] Add tests (SciPy path, fallback path, sequential update, bucket independence)
- [x] Update requirements/pyproject to include SciPy (optional)
- [x] Run tests
- [x] Commit changes (include bean file)
