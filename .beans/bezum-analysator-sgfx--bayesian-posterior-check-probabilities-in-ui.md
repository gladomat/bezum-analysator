---
# bezum-analysator-sgfx
title: Bayesian posterior check probabilities in UI
status: completed
type: milestone
priority: normal
created_at: 2026-02-05T15:35:19Z
updated_at: 2026-02-05T15:43:04Z
---

Goal: Under each month in Overview and under each weekday mean in Month Detail, display posterior probability of being checked.

Initial proposal:
- Define per-day Bernoulli: y=1 if check_message_count>0 (or check_event_count>0 depending on selected metric)
- Month posterior: p_month = Pr(y=1) with Beta prior
- Month×weekday posterior: p_{month,weekday}
- Display posterior mean + 95% credible interval

Implementation notes:
- User requested PyMC3; verify compatibility with Python version and decide whether to use PyMC3 or PyMC (with compatible model) + document choice.

## Checklist
- [x] Lock definition of “being checked” + which metric drives it
- [x] Confirm what to display (mean only vs interval)
- [x] Decide model/prior and implementation (PyMC3 vs analytic Beta-Binomial)
- [x] Add artifact generation for posterior summaries
- [x] Add API/UI rendering in Overview + Month Detail
- [x] Add tests + run analyze + serve smoke test
