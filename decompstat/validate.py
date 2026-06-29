"""Validation and inventory reporting."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import REQUIRED_COLUMNS, SchemaError, Metadata

IDENTIFIER_COLUMNS = ["sample_id", "system_id", "state_id", "method_id", "res_1", "res_2"]

UNIQUE_KEY = [
    "system_id",
    "state_id",
    "method_id",
    "sample_id",
    "res_1",
    "res_2",
    "component",
]


def validate_dataset(
    df: pd.DataFrame,
    metadata: Metadata,
    *,
    require_snapshot_assertion: bool = False,
) -> None:
    """Validate canonical data and metadata.

    Parameters
    ----------
    df
        Canonical long-format table.
    metadata
        Dataset-level metadata.
    require_snapshot_assertion
        If True, require metadata.snapshots_shared_across_methods. Comparison commands should
        set this to True; inventory commands need not.
    """
    metadata.validate()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Missing required columns: {missing}")

    if df.empty:
        raise SchemaError("Input table is empty.")

    if df[REQUIRED_COLUMNS].isna().any().any():
        cols = df[REQUIRED_COLUMNS].columns[df[REQUIRED_COLUMNS].isna().any()].tolist()
        raise SchemaError(f"Required columns contain NaN values: {cols}")

    empty_identifier_cols = [
        c for c in IDENTIFIER_COLUMNS if df[c].astype(str).str.strip().eq("").any()
    ]
    if empty_identifier_cols:
        raise SchemaError(f"Identifier columns contain empty strings: {empty_identifier_cols}")

    if not np.isfinite(df["energy_total"].to_numpy(dtype=float)).all():
        raise SchemaError("energy_total contains NaN or infinite values.")

    missing_key_cols = [c for c in UNIQUE_KEY if c not in df.columns]
    if missing_key_cols:
        raise SchemaError(f"Internal error: normalized table lacks key columns {missing_key_cols}")

    dup_mask = df.duplicated(UNIQUE_KEY, keep=False)
    if dup_mask.any():
        examples = df.loc[dup_mask, UNIQUE_KEY].head(5).to_dict(orient="records")
        raise SchemaError(f"Duplicate unique keys found. Examples: {examples}")

    if "energy_unit" in df.columns:
        units = sorted(str(u) for u in df["energy_unit"].dropna().unique())
        if len(units) > 1:
            raise SchemaError(f"Mixed energy_unit values in table: {units}")
        if units and units[0] != metadata.energy_unit:
            raise SchemaError(
                f"Row energy_unit={units[0]!r} conflicts with metadata energy_unit={metadata.energy_unit!r}"
            )

    if require_snapshot_assertion and not metadata.snapshots_shared_across_methods:
        raise SchemaError(
            "Paired comparison requires metadata.snapshots_shared_across_methods=true. "
            "The tool can check matching sample_id values, but only the user can assert that "
            "they represent the same physical snapshots."
        )


def summarize_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Return one-row-per-group inventory useful before comparisons."""
    group_cols = ["system_id", "state_id", "method_id", "component"]
    summary = (
        df.groupby(group_cols, dropna=False)
        .agg(
            n_rows=("energy_total", "size"),
            n_samples=("sample_id", "nunique"),
            n_pairs=("res_1", lambda s: len(s.index)),
            n_res_1=("res_1", "nunique"),
            n_res_2=("res_2", "nunique"),
            energy_min=("energy_total", "min"),
            energy_max=("energy_total", "max"),
        )
        .reset_index()
    )
    # n_pairs above counts rows; use unique pair count instead.
    pair_counts = (
        df.assign(_pair=df["res_1"].astype(str) + "||" + df["res_2"].astype(str))
        .groupby(group_cols, dropna=False)["_pair"]
        .nunique()
        .rename("n_unique_pairs")
        .reset_index()
    )
    return summary.drop(columns=["n_pairs"]).merge(pair_counts, on=group_cols, how="left")


def overlap_report(df_a: pd.DataFrame, df_b: pd.DataFrame, keys: list[str]) -> dict[str, int]:
    """Return overlap counts for two tables on a key set."""
    a = df_a[keys].drop_duplicates()
    b = df_b[keys].drop_duplicates()
    common = a.merge(b, on=keys, how="inner")
    return {
        "n_keys_a": int(len(a)),
        "n_keys_b": int(len(b)),
        "n_common_keys": int(len(common)),
        "n_dropped_from_a": int(len(a) - len(common)),
        "n_dropped_from_b": int(len(b) - len(common)),
    }
