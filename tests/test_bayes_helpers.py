"""Tests for Beta/Beta-Binomial helper utilities."""

from __future__ import annotations

import math

import pytest

from tg_checkstats import bayes as bayes_mod


def _normal_approx_ci(*, alpha: float, beta: float, z: float) -> tuple[float, float]:
    """Return the clamped normal-approx CI for a Beta(alpha, beta)."""
    mean = alpha / (alpha + beta)
    var = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1))
    sd = math.sqrt(var)
    return (max(0.0, mean - z * sd), min(1.0, mean + z * sd))


def test_module_defines_scipy_import_guard() -> None:
    """The bayes module defines `scipy_beta` for optional exact quantiles."""
    assert hasattr(bayes_mod, "scipy_beta")


def test_fallback_warns_once_and_matches_normal_approx(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When SciPy is unavailable, interval matches old normal approx and warns once."""
    if not hasattr(bayes_mod, "beta_posterior_summary"):
        pytest.fail("bayes_mod.beta_posterior_summary missing")

    if not hasattr(bayes_mod, "scipy_beta"):
        pytest.fail("bayes_mod.scipy_beta missing")

    monkeypatch.setattr(bayes_mod, "scipy_beta", None, raising=True)

    warn_once = getattr(bayes_mod, "_warn_scipy_missing_once", None)
    if warn_once is not None and hasattr(warn_once, "cache_clear"):
        warn_once.cache_clear()

    caplog.set_level("WARNING")
    z = 1.96
    summary1 = bayes_mod.beta_posterior_summary(
        trials=10, successes=5, prior_alpha=0.5, prior_beta=0.5, z=z
    )
    summary2 = bayes_mod.beta_posterior_summary(
        trials=10, successes=5, prior_alpha=0.5, prior_beta=0.5, z=z
    )

    assert summary1 == summary2

    alpha = 0.5 + 5.0
    beta = 0.5 + 5.0
    expected_low, expected_high = _normal_approx_ci(alpha=alpha, beta=beta, z=z)
    assert summary1.ci_low == pytest.approx(expected_low, abs=1e-12)
    assert summary1.ci_high == pytest.approx(expected_high, abs=1e-12)

    warnings = [
        record
        for record in caplog.records
        if record.levelname == "WARNING"
        and "SciPy not installed" in (record.getMessage() or "")
    ]
    assert len(warnings) == 1


def test_exact_interval_matches_scipy_when_available() -> None:
    """If SciPy is installed, the interval uses exact Beta quantiles."""
    pytest.importorskip("scipy")

    if getattr(bayes_mod, "scipy_beta", None) is None:
        pytest.fail("SciPy import guard exists but SciPy was not imported")

    summary = bayes_mod.beta_posterior_summary(
        trials=10, successes=5, prior_alpha=0.5, prior_beta=0.5
    )

    assert 0.0 <= summary.ci_low <= summary.mean <= summary.ci_high <= 1.0

    alpha = 0.5 + 5.0
    beta = 0.5 + 5.0
    expected_low, expected_high = bayes_mod.scipy_beta.interval(0.95, alpha, beta)
    assert summary.ci_low == pytest.approx(float(expected_low), abs=1e-12)
    assert summary.ci_high == pytest.approx(float(expected_high), abs=1e-12)


def test_sequential_update_equivalence() -> None:
    """Updating priors sequentially matches aggregating counts first."""
    BetaPrior = getattr(bayes_mod, "BetaPrior", None)
    beta_update_prior = getattr(bayes_mod, "beta_update_prior", None)
    if BetaPrior is None or beta_update_prior is None:
        pytest.fail("BetaPrior/beta_update_prior not implemented")

    prior = BetaPrior(alpha=0.5, beta=0.5)
    period1 = beta_update_prior(prior=prior, trials=10, successes=3)
    period2 = beta_update_prior(prior=period1, trials=7, successes=2)
    aggregated = beta_update_prior(prior=prior, trials=17, successes=5)

    assert period2.alpha == pytest.approx(aggregated.alpha)
    assert period2.beta == pytest.approx(aggregated.beta)


def test_bucketed_update_independence_and_carryover() -> None:
    """Bucket updates are independent and unchanged buckets are carried over."""
    BetaPrior = getattr(bayes_mod, "BetaPrior", None)
    beta_update_priors_by_bucket = getattr(bayes_mod, "beta_update_priors_by_bucket", None)
    if BetaPrior is None or beta_update_priors_by_bucket is None:
        pytest.fail("BetaPrior/beta_update_priors_by_bucket not implemented")

    priors = {
        "A": BetaPrior(alpha=1.0, beta=1.0),
        "B": BetaPrior(alpha=2.0, beta=3.0),
        "C": BetaPrior(alpha=5.0, beta=8.0),
    }
    counts = {"A": (10, 3), "B": (7, 2)}
    updated = beta_update_priors_by_bucket(priors_by_bucket=priors, counts_by_bucket=counts)

    assert updated["A"].alpha == pytest.approx(1.0 + 3.0)
    assert updated["A"].beta == pytest.approx(1.0 + 7.0)
    assert updated["B"].alpha == pytest.approx(2.0 + 2.0)
    assert updated["B"].beta == pytest.approx(3.0 + 5.0)
    assert updated["C"] == priors["C"]

