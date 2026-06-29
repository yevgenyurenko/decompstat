"""Autocorrelation-aware uncertainty estimates.

The estimators here are standard empirical tools. DecompStat's contribution is applying
these tools consistently to residue-pair decomposition tables, not inventing new statistics.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import warnings

import numpy as np


@dataclass(frozen=True)
class BootstrapResult:
    mean: float
    ci_low: float
    ci_high: float
    n: int
    g: float
    n_eff: float
    block_length: int
    warning: str = ""


def statistical_inefficiency(x: np.ndarray) -> float:
    """Estimate statistical inefficiency g >= 1.

    Uses pymbar if available, with a small autocorrelation fallback. For short or constant
    series the estimate is conservative and returns 1.
    """
    arr = np.asarray(x, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n < 4:
        return 1.0
    if np.nanstd(arr) == 0:
        return 1.0

    try:  # Prefer the MD/free-energy community standard when installed.
        from pymbar import timeseries  # type: ignore

        g = float(timeseries.statistical_inefficiency(arr))
        if np.isfinite(g) and g >= 1:
            return min(g, float(n))
    except Exception:
        pass

    # Fallback: initial-positive-sequence style integrated autocorrelation estimate.
    centered = arr - arr.mean()
    var = np.dot(centered, centered) / n
    if var <= 0:
        return 1.0
    # np.correlate is fine for the small v1.0 use case.
    acov = np.correlate(centered, centered, mode="full")[n - 1 :] / np.arange(n, 0, -1)
    acf = acov / var
    g = 1.0
    for rho in acf[1:]:
        if rho <= 0:
            break
        g += 2.0 * float(rho)
        if g > n:
            return float(n)
    return max(1.0, min(float(g), float(n)))


def choose_block_length(x: np.ndarray, block_length: int | None = None) -> tuple[int, float, float, str]:
    """Choose moving-block length from statistical inefficiency.

    Returns block length, g, N_eff, and a warning string.
    """
    arr = np.asarray(x, dtype=float)
    n = len(arr)
    if n == 0:
        raise ValueError("Cannot choose block length for an empty series.")
    g = statistical_inefficiency(arr)
    n_eff = max(1.0, n / g)
    warning = ""
    if block_length is None:
        block_length = max(1, int(ceil(g)))
    block_length = max(1, min(int(block_length), max(1, n // 2) if n > 2 else 1))

    if n < 20:
        warning = "short_series_uncertainty_exploratory"
    if g > n / 4 and n >= 4:
        warning = "large_g_relative_to_n_interpret_ci_with_caution"
    return block_length, g, n_eff, warning


def moving_block_indices(n: int, block_length: int, rng: np.random.Generator) -> np.ndarray:
    """Return indices from a moving-block bootstrap sample of length n."""
    if n <= 0:
        raise ValueError("n must be positive")
    block_length = max(1, min(int(block_length), n))
    starts = rng.integers(0, n - block_length + 1, size=int(ceil(n / block_length)))
    idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
    return idx


def block_bootstrap_mean(
    x: np.ndarray,
    *,
    n_boot: int = 1000,
    ci: float = 0.95,
    seed: int = 12345,
    block_length: int | None = None,
) -> BootstrapResult:
    """Moving-block bootstrap confidence interval for the mean."""
    arr = np.asarray(x, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        raise ValueError("Cannot bootstrap an empty series.")
    if len(arr) == 1:
        val = float(arr[0])
        return BootstrapResult(val, val, val, 1, 1.0, 1.0, 1, "single_sample_no_uncertainty")

    b, g, n_eff, warning = choose_block_length(arr, block_length)
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = moving_block_indices(len(arr), b, rng)
        boots[i] = float(np.mean(arr[idx]))

    alpha = (1.0 - ci) / 2.0
    lo, hi = np.quantile(boots, [alpha, 1.0 - alpha])
    return BootstrapResult(
        mean=float(np.mean(arr)),
        ci_low=float(lo),
        ci_high=float(hi),
        n=int(len(arr)),
        g=float(g),
        n_eff=float(n_eff),
        block_length=int(b),
        warning=warning,
    )


def naive_sem(x: np.ndarray) -> float:
    """Naive SEM for comparison/reporting only; do not use as primary uncertainty."""
    arr = np.asarray(x, dtype=float)
    if len(arr) < 2:
        return float("nan")
    return float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
