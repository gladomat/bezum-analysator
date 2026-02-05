"""Bayesian helpers for simple posterior probability summaries.

The UI wants a "posterior probability of being checked" that is fast to compute
and stable across runs. For the current use-case we model day-level "check
present" as a Bernoulli outcome and use a conjugate Beta prior.

We intentionally avoid MCMC sampling (PyMC/PyMC3) here for speed and to keep the
tool lightweight. The posterior is analytic (Beta-Binomial conjugacy).
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BetaPosteriorSummary:
    """Summary stats for a Beta posterior over a Bernoulli probability."""

    trials: int
    successes: int
    alpha: float
    beta: float
    mean: float
    ci_low: float
    ci_high: float


def beta_posterior_summary(
    *,
    trials: int,
    successes: int,
    prior_alpha: float = 0.5,
    prior_beta: float = 0.5,
    z: float = 1.96,
) -> BetaPosteriorSummary:
    """Compute an analytic Beta posterior and a normal-approx 95% interval.

    Args:
        trials: Number of Bernoulli trials (n >= 0).
        successes: Number of successes (0 <= s <= n).
        prior_alpha: Beta prior alpha (Jeffreys prior default: 0.5).
        prior_beta: Beta prior beta (Jeffreys prior default: 0.5).
        z: Z-score for the normal approximation (1.96 ≈ 95%).

    Returns:
        A BetaPosteriorSummary with posterior parameters, mean, and an
        approximate credible interval. The interval is clamped to [0, 1].
    """
    if trials < 0:
        raise ValueError("trials must be >= 0")
    if successes < 0 or successes > trials:
        raise ValueError("successes must satisfy 0 <= successes <= trials")
    if prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("prior_alpha/prior_beta must be > 0")

    alpha = prior_alpha + float(successes)
    beta = prior_beta + float(trials - successes)
    mean = alpha / (alpha + beta)

    # Beta variance: ab / ((a+b)^2 (a+b+1))
    var = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1))
    sd = math.sqrt(var)
    low = max(0.0, mean - z * sd)
    high = min(1.0, mean + z * sd)

    return BetaPosteriorSummary(
        trials=trials,
        successes=successes,
        alpha=alpha,
        beta=beta,
        mean=mean,
        ci_low=low,
        ci_high=high,
    )

