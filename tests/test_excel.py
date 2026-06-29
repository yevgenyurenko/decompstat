import pandas as pd

from decompstat.excel import read_mutation_score_excel


def test_read_mutation_score_excel_handles_shifted_snapshot_block(tmp_path):
    path = tmp_path / "mutation_scores.xlsx"

    data = [[None for _ in range(11)] for _ in range(4)]

    data[0][0] = "Traj-1"
    data[1][0] = "0.56 ns"
    data[1][5] = "2.55 ns"

    data[2][0] = "ALA"
    data[2][1] = -78.0
    data[2][2] = -83.0
    data[2][3] = 5.0
    data[2][4] = "no"

    data[3][0] = "ARG"
    data[3][1] = -87.0
    data[3][2] = -83.0
    data[3][3] = -4.0
    data[3][4] = "yes"

    data[2][6] = "ALA"
    data[2][7] = -77.0
    data[2][8] = -83.0
    data[2][9] = 6.0
    data[2][10] = "no"

    data[3][6] = "ARG"
    data[3][7] = -84.0
    data[3][8] = -83.0
    data[3][9] = -1.0
    data[3][10] = "yes"

    df = pd.DataFrame(data)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="B16", header=False, index=False)

    out = read_mutation_score_excel(path, sheets=["B16"])

    assert len(out) == 4
    assert out["sample_id"].nunique() == 2
    assert set(out["mutation_id"]) == {"ALA", "ARG"}
    assert set(out["energy_total"]) == {5.0, -4.0, 6.0, -1.0}
