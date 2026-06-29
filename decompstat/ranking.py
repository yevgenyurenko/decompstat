"""Hotspot rank-stability analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .compare import filter_by_selector, OBJECT_KEYS
from .schema import Metadata, SchemaError
from .validate import validate_dataset
from .uncertainty import choose_block_length, moving_block_indices


def _dense_rank_more_negative_first(values: pd.Series) -> pd.Series:
    """Rank energies so more negative values receive rank 1."""
    return values.rank(method="dense", ascending=True).astype(int)


def rank_stability(
    df: pd.DataFrame,
    metadata: Metadata,
    group: str | dict[str, str],
    *,
    top_k: int = 10,
    n_boot: int = 1000,
    seed: int = 12345,
) -> pd.DataFrame:
    """Bootstrap hotspot rank stability for one selected group.

    Bootstrap resampling is performed over sample_id values, not over rows. Each resampled
    snapshot contributes all residue-pair rows belonging to that sample.
    """
    validate_dataset(df, metadata, require_snapshot_assertion=False)
    gdf = filter_by_selector(df, group)
    if gdf["sample_id"].nunique() < 2:
        raise SchemaError("Rank stability requires at least two distinct sample_id values.")

    point = (
        gdf.groupby(OBJECT_KEYS, sort=True)["energy_total"]
        .mean()
        .rename("mean_energy")
        .reset_index()
    )
    point["point_rank"] = _dense_rank_more_negative_first(point["mean_energy"])

    # Estimate block length from the per-snapshot mean energy series.
    by_sample_mean = gdf.groupby("sample_id", sort=True)["energy_total"].mean()
    sample_ids = by_sample_mean.index.to_numpy()
    block_length, g, n_eff, warning = choose_block_length(by_sample_mean.to_numpy())

    rows_by_sample = {sid: part for sid, part in gdf.groupby("sample_id", sort=False)}
    rng = np.random.default_rng(seed)
    rank_records: dict[tuple[str, str, str], list[int]] = {
        tuple(row): [] for row in point[OBJECT_KEYS].to_numpy()
    }

    for _ in range(n_boot):
        idx = moving_block_indices(len(sample_ids), block_length, rng)
        sampled_frames = [rows_by_sample[sample_ids[i]] for i in idx]
        boot_df = pd.concat(sampled_frames, ignore_index=True)
        means = boot_df.groupby(OBJECT_KEYS, sort=True)["energy_total"].mean()
        ranks = _dense_rank_more_negative_first(means)
        for key, rank in ranks.items():
            rank_records[tuple(key)].append(int(rank))

    out_rows = []
    for _, row in point.iterrows():
        key = (row["res_1"], row["res_2"], row["component"])
        ranks = np.asarray(rank_records[key], dtype=float)
        out_rows.append(
            {
                "res_1": key[0],
                "res_2": key[1],
                "component": key[2],
                "mean_energy": float(row["mean_energy"]),
                "point_rank": int(row["point_rank"]),
                "median_rank": float(np.median(ranks)),
                "rank_ci_low": float(np.quantile(ranks, 0.025)),
                "rank_ci_high": float(np.quantile(ranks, 0.975)),
                "top_k_probability": float(np.mean(ranks <= top_k)),
                "g": float(g),
                "n_eff": float(n_eff),
                "block_length": int(block_length),
                "warning": warning,
            }
        )
    return pd.DataFrame(out_rows).sort_values("point_rank").reset_index(drop=True)


def rank_agreement(
    df: pd.DataFrame,
    metadata: Metadata,
    group_a: str | dict[str, str],
    group_b: str | dict[str, str],
    *,
    top_k: int = 10,
) -> dict[str, float | int]:
    """Compare hotspot rankings on the common residue-pair set.

    Returns Spearman rho and top-k Jaccard overlap. It intentionally uses only the common
    residue-pair universe, because comparing rankings over different universes is undefined.
    """
    validate_dataset(df, metadata, require_snapshot_assertion=False)
    a = filter_by_selector(df, group_a)
    b = filter_by_selector(df, group_b)
    ma = a.groupby(OBJECT_KEYS, sort=True)["energy_total"].mean().rename("energy_a")
    mb = b.groupby(OBJECT_KEYS, sort=True)["energy_total"].mean().rename("energy_b")
    common = pd.concat([ma, mb], axis=1, join="inner").dropna()
    if len(common) < 2:
        raise SchemaError("At least two common residue pairs are required for rank agreement.")

    rank_a = _dense_rank_more_negative_first(common["energy_a"])
    rank_b = _dense_rank_more_negative_first(common["energy_b"])
    rho, pval = spearmanr(rank_a.to_numpy(), rank_b.to_numpy())

    top_a = set(rank_a[rank_a <= top_k].index)
    top_b = set(rank_b[rank_b <= top_k].index)
    union = top_a | top_b
    jaccard = len(top_a & top_b) / len(union) if union else 1.0
    return {
        "n_common_pairs": int(len(common)),
        "spearman_rho": float(rho),
        "spearman_pvalue": float(pval),
        "top_k": int(top_k),
        "top_k_jaccard": float(jaccard),
    }
