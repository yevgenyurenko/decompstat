import numpy as np
import pandas as pd
import pytest

from decompstat.io import normalize_dataframe
from decompstat.schema import Metadata, SchemaError
from decompstat.compare import paired_comparison


def make_compare_df():
    rows = []
    for sample in ["s1", "s2", "s3"]:
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "A", "res_1": "R1", "res_2": "R2", "energy_total": 1.0})
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "B", "res_1": "R1", "res_2": "R2", "energy_total": 3.0})
    return normalize_dataframe(pd.DataFrame(rows))


def test_paired_compare_constant_difference():
    df = make_compare_df()
    meta = Metadata(snapshots_shared_across_methods=True)
    out, coverage = paired_comparison(df, meta, {"method_id": "A"}, {"method_id": "B"}, n_boot=50)
    assert coverage["n_common_keys"] == 3
    assert np.isclose(out.loc[0, "mean_diff_target_minus_ref"], 2.0)
    assert out.loc[0, "ci_low"] <= 2.0 <= out.loc[0, "ci_high"]


def test_compare_uses_sample_id_not_row_order():
    df = make_compare_df()
    # Reorder method B rows; correct result must be unchanged because join is on sample_id.
    mask_b = df["method_id"] == "B"
    df_b = df[mask_b].iloc[::-1]
    df = pd.concat([df[~mask_b], df_b], ignore_index=True)
    meta = Metadata(snapshots_shared_across_methods=True)
    out, _ = paired_comparison(df, meta, {"method_id": "A"}, {"method_id": "B"}, n_boot=50)
    assert np.isclose(out.loc[0, "mean_diff_target_minus_ref"], 2.0)


def test_compare_raises_on_empty_overlap():
    df = make_compare_df()
    df.loc[df["method_id"] == "B", "sample_id"] = ["x1", "x2", "x3"]
    meta = Metadata(snapshots_shared_across_methods=True)
    with pytest.raises(SchemaError):
        paired_comparison(df, meta, {"method_id": "A"}, {"method_id": "B"}, n_boot=50)

def test_compare_reports_flipped_pair_orientation_as_partial_overlap():
    rows = []
    for sample in ["s1", "s2", "s3"]:
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "A", "res_1": "R1", "res_2": "R2", "energy_total": 1.0})
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "B", "res_1": "R1", "res_2": "R2", "energy_total": 2.0})
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "A", "res_1": "R3", "res_2": "R4", "energy_total": 3.0})
        rows.append({"sample_id": sample, "system_id": "sys", "state_id": "WT", "method_id": "B", "res_1": "R4", "res_2": "R3", "energy_total": 4.0})

    df = normalize_dataframe(pd.DataFrame(rows))
    meta = Metadata(snapshots_shared_across_methods=True)
    out, coverage = paired_comparison(df, meta, {"method_id": "A"}, {"method_id": "B"}, n_boot=20)

    assert coverage["n_common_keys"] == 3
    assert coverage["n_dropped_from_a"] == 3
    assert coverage["n_dropped_from_b"] == 3
    assert out.loc[0, "n_pair_keys_dropped_from_ref"] == 3
    assert out.loc[0, "n_pair_keys_dropped_from_target"] == 3
    assert "partial_pair_key_overlap" in out.loc[0, "warning"]
