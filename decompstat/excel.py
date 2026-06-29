"""Converters for project-specific Excel mutation-score workbooks."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


_NS_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*ns\s*$", re.IGNORECASE)


def _time_ps(label: str) -> int:
    match = _NS_RE.match(str(label))
    if not match:
        raise ValueError(f"Cannot parse snapshot time label: {label!r}")
    return int(round(float(match.group(1)) * 1000))


def _snapshot_blocks(df: pd.DataFrame) -> list[tuple[int, str, str]]:
    blocks: list[tuple[int, str, str]] = []
    current_traj: str | None = None

    for col in range(df.shape[1]):
        traj_value = df.iat[0, col]
        if pd.notna(traj_value):
            current_traj = str(traj_value).strip()

        time_value = df.iat[1, col]
        if pd.notna(time_value) and _NS_RE.match(str(time_value)):
            if current_traj is None:
                raise ValueError(f"Snapshot at column {col} has no trajectory label")
            blocks.append((col, current_traj, str(time_value).strip()))

    return blocks


def _data_start_col(df: pd.DataFrame, time_col: int) -> int:
    """Find the first actual mutation column after a snapshot time cell."""
    for col in range(time_col, min(time_col + 3, df.shape[1])):
        if col + 4 >= df.shape[1]:
            continue

        mutation = df.iat[2, col]
        score = df.iat[2, col + 3]

        if pd.isna(mutation) or pd.isna(score):
            continue

        try:
            float(score)
        except (TypeError, ValueError):
            continue

        return col

    raise ValueError(f"Cannot locate data columns for snapshot starting at column {time_col}")


def read_mutation_score_excel(
    path: str | Path,
    *,
    sheets: list[str] | None = None,
    system_id: str = "insulin_ir",
    method_id: str = "SQM_MM_LEAP",
    component: str = "ddg_score",
) -> pd.DataFrame:
    """Convert a wide mutation-score workbook into canonical DecompStat rows.

    Expected block layout per snapshot:
    mutation, mutant_energy, wt_energy, score, favourable_flag.
    """

    path = Path(path)
    xl = pd.ExcelFile(path)
    selected_sheets = sheets or xl.sheet_names

    rows: list[dict[str, object]] = []

    for sheet in selected_sheets:
        if sheet not in xl.sheet_names:
            raise ValueError(f"Sheet {sheet!r} not found in {path}")

        df = pd.read_excel(path, sheet_name=sheet, header=None)
        blocks = _snapshot_blocks(df)

        for time_col, traj_label, time_label in blocks:
            data_start_col = _data_start_col(df, time_col)
            replica_id = traj_label.lower().replace("-", "")
            time_ps = _time_ps(time_label)
            sample_id = f"{replica_id}_t{time_label.replace(' ', '')}"

            for row_idx in range(2, df.shape[0]):
                mutation = df.iat[row_idx, data_start_col]
                if pd.isna(mutation):
                    continue

                mutation_id = str(mutation).strip()
                if not mutation_id:
                    continue

                try:
                    mutant_energy = df.iat[row_idx, data_start_col + 1]
                    wt_energy = df.iat[row_idx, data_start_col + 2]
                    score = df.iat[row_idx, data_start_col + 3]
                    favourable = df.iat[row_idx, data_start_col + 4]
                except IndexError as exc:
                    raise ValueError(
                        f"Incomplete snapshot block in sheet {sheet!r}, column {data_start_col}"
                    ) from exc

                if pd.isna(score):
                    continue

                rows.append(
                    {
                        "system_id": system_id,
                        "state_id": f"{sheet}_{mutation_id}",
                        "method_id": method_id,
                        "sample_id": sample_id,
                        "replica_id": replica_id,
                        "time_ps": time_ps,
                        "res_1": f"INS:{sheet}",
                        "res_2": "IR_SITE1_FRAGMENT",
                        "component": component,
                        "energy_total": float(score),
                        "mutation_id": mutation_id,
                        "mutant_energy": float(mutant_energy),
                        "wt_energy": float(wt_energy),
                        "is_favourable": str(favourable).strip().lower() == "yes",
                    }
                )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    return out.sort_values(["res_1", "mutation_id", "sample_id"]).reset_index(drop=True)
