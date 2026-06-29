"""Paired comparisons of methods, states, and protocols."""

from __future__ import annotations

from dataclasses import asdict
import pandas as pd

from .schema import Metadata, SchemaError
from .validate import validate_dataset, overlap_report
from .uncertainty import block_bootstrap_mean

PAIR_KEYS = ["sample_id", "res_1", "res_2", "component"]
OBJECT_KEYS = ["res_1", "res_2", "component"]


def parse_selector(selector: str | dict[str, str]) -> dict[str, str]:
    """Parse 'col=value,col2=value2' selectors used by the CLI."""
    if isinstance(selector, dict):
        return selector
    out: dict[str, str] = {}
    if not selector:
        return out
    for part in selector.split(","):
        if "=" not in part:
            raise ValueError(f"Selector part {part!r} must be of form column=value")
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def filter_by_selector(df: pd.DataFrame, selector: str | dict[str, str]) -> pd.DataFrame:
    """Filter a DataFrame by exact-match selector."""
    sel = parse_selector(selector)
    out = df
    for col, value in sel.items():
        if col not in out.columns:
            raise SchemaError(f"Selector references missing column {col!r}")
        out = out[out[col].astype(str) == str(value)]
    if out.empty:
        raise SchemaError(f"Selector produced no rows: {sel}")
    return out.copy()


def paired_comparison(
    df: pd.DataFrame,
    metadata: Metadata,
    ref: str | dict[str, str],
    target: str | dict[str, str],
    *,
    n_boot: int = 1000,
    seed: int = 12345,
    min_overlap: int = 2,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compare two selected groups using shared sample_id/residue-pair keys.

    The statistic is target - ref, computed per matching sample/residue pair. The function
    refuses comparisons unless metadata asserts that sample_id values are shared physical
    snapshots across methods.
    """
    validate_dataset(df, metadata, require_snapshot_assertion=True)
    a = filter_by_selector(df, ref)
    b = filter_by_selector(df, target)
    coverage = overlap_report(a, b, PAIR_KEYS)
    if coverage["n_common_keys"] < min_overlap:
        raise SchemaError(f"Insufficient paired overlap: {coverage}")

    merged = a.merge(
        b,
        on=PAIR_KEYS,
        suffixes=("_ref", "_target"),
        how="inner",
        validate="one_to_one",
    )
    merged["delta"] = merged["energy_total_target"] - merged["energy_total_ref"]

    rows = []
    for keys, gdf in merged.groupby(OBJECT_KEYS, sort=True):
        res = block_bootstrap_mean(gdf["delta"].to_numpy(), n_boot=n_boot, seed=seed)
        ref_mean = float(gdf["energy_total_ref"].mean())
        target_mean = float(gdf["energy_total_target"].mean())
        row = {
            "res_1": keys[0],
            "res_2": keys[1],
            "component": keys[2],
            "n_samples_used": int(gdf["sample_id"].nunique()),
            "mean_ref": ref_mean,
            "mean_target": target_mean,
            "mean_diff_target_minus_ref": res.mean,
            "ci_low": res.ci_low,
            "ci_high": res.ci_high,
            "ci_excludes_zero": bool(res.ci_low > 0 or res.ci_high < 0),
            "g": res.g,
            "n_eff": res.n_eff,
            "block_length": res.block_length,
            "warning": res.warning,
        }
        rows.append(row)
    result = pd.DataFrame(rows).sort_values(["component", "res_1", "res_2"]).reset_index(drop=True)
    return result, coverage


def mutant_scan(
    df: pd.DataFrame,
    metadata: Metadata,
    *,
    method_id: str,
    wt_state: str,
    mutant_state: str,
    n_boot: int = 1000,
    seed: int = 12345,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """WT-vs-mutant comparison as a special case of paired comparison."""
    return paired_comparison(
        df,
        metadata,
        ref={"method_id": method_id, "state_id": wt_state},
        target={"method_id": method_id, "state_id": mutant_state},
        n_boot=n_boot,
        seed=seed,
    )
