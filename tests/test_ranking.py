import numpy as np
import pandas as pd

from decompstat.io import normalize_dataframe
from decompstat.schema import Metadata
from decompstat.ranking import rank_stability, rank_agreement


def make_rank_df():
    rows = []
    for sample in ["s1", "s2", "s3", "s4"]:
        for method, values in {"A": [-3.0, -2.0, -1.0], "B": [-3.1, -1.1, -2.1]}.items():
            for idx, e in enumerate(values):
                rows.append({
                    "sample_id": sample,
                    "system_id": "sys",
                    "state_id": "WT",
                    "method_id": method,
                    "res_1": f"R{idx}",
                    "res_2": "LIG",
                    "energy_total": e,
                })
    return normalize_dataframe(pd.DataFrame(rows))


def test_rank_stability_top_hotspot_probability_one():
    df = make_rank_df()
    meta = Metadata()
    out = rank_stability(df, meta, {"method_id": "A"}, top_k=1, n_boot=50, seed=3)
    top = out.sort_values("point_rank").iloc[0]
    assert top["top_k_probability"] == 1.0


def test_rank_agreement_common_pairs_only():
    df = make_rank_df()
    # Add method B-only pair. It must not enter common-pair rank agreement.
    extra = pd.DataFrame([{
        "sample_id": "s1", "system_id": "sys", "state_id": "WT", "method_id": "B",
        "res_1": "EXTRA", "res_2": "LIG", "energy_total": -99.0,
    }])
    df = normalize_dataframe(pd.concat([df, extra], ignore_index=True))
    meta = Metadata()
    result = rank_agreement(df, meta, {"method_id": "A"}, {"method_id": "B"}, top_k=2)
    assert result["n_common_pairs"] == 3
