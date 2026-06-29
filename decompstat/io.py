"""Input/output helpers."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from .schema import DEFAULT_COMPONENT, REQUIRED_COLUMNS, SchemaError, Metadata, load_metadata
from .validate import validate_dataset


def read_dataset(path: str | Path, metadata_path: str | Path | None = None) -> tuple[pd.DataFrame, Metadata]:
    """Read canonical DecompStat CSV and metadata, normalize dtypes, and validate."""
    df = pd.read_csv(path)
    meta = load_metadata(metadata_path)
    df = normalize_dataframe(df)
    validate_dataset(df, meta, require_snapshot_assertion=False)
    return df, meta


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize optional columns and dtypes without changing user semantics."""
    out = df.copy()
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise SchemaError(f"Missing required columns: {missing}")

    # Keep identifiers as strings to prevent 001/1 mismatches and mixed int/string keys.
    for col in ["sample_id", "system_id", "state_id", "method_id", "res_1", "res_2"]:
        out[col] = out[col].astype(str)

    if "component" not in out.columns:
        out["component"] = DEFAULT_COMPONENT
    else:
        out["component"] = out["component"].fillna(DEFAULT_COMPONENT).astype(str)

    if "replica_id" in out.columns:
        out["replica_id"] = out["replica_id"].fillna("replica_0").astype(str)

    out["energy_total"] = pd.to_numeric(out["energy_total"], errors="coerce")
    return out


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    """Write a deterministic CSV table."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
