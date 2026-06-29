import numpy as np

from decompstat.uncertainty import statistical_inefficiency, block_bootstrap_mean, naive_sem


def ar1(n=500, rho=0.85, seed=1):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    eps = rng.normal(size=n)
    for i in range(1, n):
        x[i] = rho * x[i-1] + eps[i]
    return x


def test_ar1_statistical_inefficiency_greater_than_one():
    x = ar1()
    g = statistical_inefficiency(x)
    assert g > 1.0


def test_block_bootstrap_ci_wider_than_naive_sem_scale_for_ar1():
    x = ar1()
    res = block_bootstrap_mean(x, n_boot=200, seed=2)
    width = (res.ci_high - res.ci_low) / 2.0
    assert res.n_eff < res.n
    assert width > naive_sem(x)
