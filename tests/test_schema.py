import pandas as pd
import pytest

from decompstat.io import normalize_dataframe
from decompstat.schema import Metadata, SchemaError
from decompstat.validate import validate_dataset


def valid_df():
    return normalize_dataframe(pd.DataFrame({
        "sample_id": ["s1", "s2"],
        "system_id": ["sys", "sys"],
        "state_id": ["WT", "WT"],
        "method_id": ["A", "A"],
        "res_1": ["R1", "R1"],
        "res_2": ["R2", "R2"],
        "energy_total": [-1.0, -1.1],
    }))


def test_schema_missing_required_column():
    df = pd.DataFrame({"sample_id": ["s1"], "energy_total": [-1.0]})
    with pytest.raises(SchemaError):
        normalize_dataframe(df)


def test_schema_rejects_nan_energy():
    df = valid_df()
    df.loc[0, "energy_total"] = float("nan")
    with pytest.raises(SchemaError):
        validate_dataset(df, Metadata())


def test_schema_rejects_duplicate_keys():
    df = pd.concat([valid_df(), valid_df().iloc[[0]]], ignore_index=True)
    with pytest.raises(SchemaError):
        validate_dataset(df, Metadata())


def test_comparison_requires_snapshot_assertion():
    df = valid_df()
    with pytest.raises(SchemaError):
        validate_dataset(df, Metadata(snapshots_shared_across_methods=False), require_snapshot_assertion=True)
