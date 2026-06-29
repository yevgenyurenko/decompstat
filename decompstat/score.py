"""Summary statistics for already-computed snapshot-level scores."""

from __future__ import annotations

import pandas as pd

from .schema import Metadata
from .validate import validate_dataset
from .compare import filter_by_selector


def score_summary(
    df: pd.DataFrame,
    metadata: Metadata,
    *,
    group: str | dict[str, str] | None = None,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Summarize already-computed scores over snapshots.

    This is for tables where energy_total already stores a score such as
    ddg_score. No WT-vs-mutant subtraction is done here.
    """
    validate_dataset(df, metadata, require_snapshot_assertion=False)

    data = df.copy()
    if group:
        data = filter_by_selector(data, group)

    group_cols = ["system_id", "state_id", "method_id", "res_1", "res_2", "component"]
    if "mutation_id" in data.columns:
        group_cols.append("mutation_id")

    rows = []
    for keys, gdf in data.groupby(group_cols, sort=True):
        values = gdf["energy_total"].astype(float)
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)))
        row.update(
            {
                "n_rows": int(len(gdf)),
                "n_samples": int(gdf["sample_id"].nunique()),
                "mean_score": float(values.mean()),
                "sd_score": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "min_score": float(values.min()),
                "max_score": float(values.max()),
                "threshold": float(threshold),
                "n_favourable": int((values <= threshold).sum()),
                "fraction_favourable": float((values <= threshold).mean()),
            }
        )
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values(["method_id", "component", "mean_score"]).reset_index(drop=True)
    out["rank_by_mean_score"] = out.groupby(["method_id", "component"])["mean_score"].rank(
        method="min", ascending=True
    ).astype(int)
    return out
