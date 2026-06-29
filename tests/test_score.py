import pandas as pd

from decompstat.schema import Metadata
from decompstat.score import score_summary


def test_score_summary_ranks_and_favourable_fraction():
    df = pd.DataFrame(
        {
            "system_id": ["s", "s", "s", "s"],
            "state_id": ["B16_ARG", "B16_ARG", "B16_ASP", "B16_ASP"],
            "method_id": ["m", "m", "m", "m"],
            "sample_id": ["t1", "t2", "t1", "t2"],
            "res_1": ["INS:B16", "INS:B16", "INS:B16", "INS:B16"],
            "res_2": ["IR_SITE1", "IR_SITE1", "IR_SITE1", "IR_SITE1"],
            "component": ["ddg_score", "ddg_score", "ddg_score", "ddg_score"],
            "energy_total": [-2.0, 1.0, 5.0, 7.0],
            "mutation_id": ["ARG", "ARG", "ASP", "ASP"],
        }
    )
    meta = Metadata(**{
        "schema_version": "0.1",
        "energy_unit": "kcal/mol",
        "sign_convention": "negative_is_stabilizing",
        "snapshots_shared_across_methods": True,
        "snapshot_definition": "test snapshots",
        "provenance": {},
    })

    out = score_summary(df, meta, group="method_id=m", threshold=0.5)

    arg = out[out["mutation_id"] == "ARG"].iloc[0]
    asp = out[out["mutation_id"] == "ASP"].iloc[0]

    assert arg["n_samples"] == 2
    assert arg["n_favourable"] == 1
    assert arg["fraction_favourable"] == 0.5
    assert arg["rank_by_mean_score"] == 1

    assert asp["fraction_favourable"] == 0.0
    assert asp["rank_by_mean_score"] == 2
