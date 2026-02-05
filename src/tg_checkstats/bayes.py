"""Bayesian helpers for simple posterior probability summaries.

The UI wants a "posterior probability of being checked" that is fast to compute
and stable across runs. For the current use-case we model day-level "check
present" as a Bernoulli outcome and use a conjugate Beta prior.

We intentionally avoid MCMC sampling (PyMC/PyMC3) here for speed and to keep the
tool lightweight. The posterior is analytic (Beta-Binomial conjugacy).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import math

try:
    from scipy.stats import beta as scipy_beta
except ImportError:  # pragma: no cover
    scipy_beta = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BetaPrior:
    """A Beta prior represented by its alpha/beta parameters."""

    alpha: float
    beta: float


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


@lru_cache(maxsize=1)
def _warn_scipy_missing_once() -> None:
    """Log a one-time warning that SciPy is unavailable for exact quantiles."""
    logger.warning(
        "SciPy not installed; using normal approximation for Beta credible interval."
    )


def _beta_normal_approx_ci(*, alpha: float, beta: float, z: float) -> tuple[float, float]:
    """Compute a clamped normal-approx CI for a Beta(alpha, beta)."""
    mean = alpha / (alpha + beta)
    var = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1))
    sd = math.sqrt(var)
    low = max(0.0, mean - z * sd)
    high = min(1.0, mean + z * sd)
    return low, high


def beta_posterior_summary(
    *,
    trials: int,
    successes: int,
    prior_alpha: float = 0.5,
    prior_beta: float = 0.5,
    z: float = 1.96,
) -> BetaPosteriorSummary:
    """Compute an analytic Beta posterior and a central credible interval.

    Args:
        trials: Number of Bernoulli trials (n >= 0).
        successes: Number of successes (0 <= s <= n).
        prior_alpha: Beta prior alpha (Jeffreys prior default: 0.5).
        prior_beta: Beta prior beta (Jeffreys prior default: 0.5).
        z: Z-score for the normal approximation (1.96 ≈ 95%). If SciPy is
            available, this parameter is ignored and exact Beta quantiles are
            used instead.

    Returns:
        A BetaPosteriorSummary with posterior parameters, mean, and an
        exact (if SciPy installed) or approximate credible interval. The
        interval is clamped to [0, 1].
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

    low: float
    high: float
    if scipy_beta is not None:
        low = float(scipy_beta.ppf(0.025, alpha, beta))
        high = float(scipy_beta.ppf(0.975, alpha, beta))
        if math.isnan(low) or math.isnan(high):
            low, high = _beta_normal_approx_ci(alpha=alpha, beta=beta, z=z)
    else:
        _warn_scipy_missing_once()
        low, high = _beta_normal_approx_ci(alpha=alpha, beta=beta, z=z)

    low = max(0.0, min(1.0, low))
    high = max(0.0, min(1.0, high))

    return BetaPosteriorSummary(
        trials=trials,
        successes=successes,
        alpha=alpha,
        beta=beta,
        mean=mean,
        ci_low=low,
        ci_high=high,
    )


def beta_update_prior(*, prior: BetaPrior, trials: int, successes: int) -> BetaPrior:
    """Update a Beta prior with Binomial counts (posterior becomes next prior).

    Args:
        prior: The current Beta prior parameters.
        trials: Number of Bernoulli trials (n >= 0).
        successes: Number of successes (0 <= s <= n).

    Returns:
        The updated BetaPrior with alpha/beta incremented by successes/failures.
    """
    if trials < 0:
        raise ValueError("trials must be >= 0")
    if successes < 0 or successes > trials:
        raise ValueError("successes must satisfy 0 <= successes <= trials")
    if prior.alpha <= 0 or prior.beta <= 0:
        raise ValueError("prior.alpha/prior.beta must be > 0")

    return BetaPrior(
        alpha=prior.alpha + float(successes),
        beta=prior.beta + float(trials - successes),
    )


def beta_update_priors_by_bucket(
    *,
    priors_by_bucket: dict[str, BetaPrior],
    counts_by_bucket: dict[str, tuple[int, int]],
    default_prior: BetaPrior = BetaPrior(0.5, 0.5),
) -> dict[str, BetaPrior]:
    """Update independent Beta priors for each bucket key.

    Behavior:
    - Buckets present in `counts_by_bucket` are updated from their existing prior
      (or `default_prior` if missing).
    - Buckets not present in `counts_by_bucket` are carried forward unchanged.

    Args:
        priors_by_bucket: Current priors keyed by bucket.
        counts_by_bucket: Mapping bucket -> (trials, successes) for this update.
        default_prior: Prior to use when a bucket has no existing state.

    Returns:
        A new dict of updated priors (input dicts are not mutated).
    """
    updated: dict[str, BetaPrior] = dict(priors_by_bucket)
    for bucket, (trials, successes) in counts_by_bucket.items():
        prior = priors_by_bucket.get(bucket, default_prior)
        updated[bucket] = beta_update_prior(
            prior=prior, trials=trials, successes=successes
        )
    return updated


def beta_summaries_by_bucket(
    *,
    priors_by_bucket: dict[str, BetaPrior],
    counts_by_bucket: dict[str, tuple[int, int]] | None = None,
    default_prior: BetaPrior = BetaPrior(0.5, 0.5),
) -> dict[str, BetaPosteriorSummary]:
    """Compute Beta posterior summaries per bucket.

    Args:
        priors_by_bucket: Current priors keyed by bucket.
        counts_by_bucket: Optional mapping bucket -> (trials, successes). When
            provided, summaries reflect the posterior after applying these
            counts to the bucket's prior. When omitted, each bucket is
            summarized using its current prior (equivalently trials=0).
        default_prior: Prior to use when `counts_by_bucket` includes a bucket
            with no existing prior.

    Returns:
        A dict bucket -> BetaPosteriorSummary, using `beta_posterior_summary`
        for interval consistency.
    """
    keys: set[str] = set(priors_by_bucket)
    if counts_by_bucket is not None:
        keys |= set(counts_by_bucket)

    summaries: dict[str, BetaPosteriorSummary] = {}
    for bucket in sorted(keys):
        prior = priors_by_bucket.get(bucket, default_prior)
        trials = 0
        successes = 0
        if counts_by_bucket is not None:
            trials, successes = counts_by_bucket.get(bucket, (0, 0))

        summaries[bucket] = beta_posterior_summary(
            trials=trials,
            successes=successes,
            prior_alpha=prior.alpha,
            prior_beta=prior.beta,
        )

    return summaries
