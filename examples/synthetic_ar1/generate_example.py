"""Generate a small synthetic DecompStat dataset with known AR(1) autocorrelation.

The data are artificial and intended for tests/tutorials only. They contain two methods,
two states, and a small set of generic residue-pair interaction energies. Method B has a
known offset relative to Method A for selected pairs, and the alternate state perturbs one
hotspot. No biological system or parser format is implied.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml


def ar1(n: int, rho: float, sigma: float, rng: np.random.Generator) -> np.ndarray:
    x = np.zeros(n)
    eps = rng.normal(0.0, sigma, size=n)
    for i in range(1, n):
        x[i] = rho * x[i - 1] + eps[i]
    return x


def main() -> None:
    rng = np.random.default_rng(20260629)
    n = 100
    pairs = [
        ("PROT:A45:ASP", "LIG:X1", -4.0),
        ("PROT:B67:PHE", "LIG:X2", -3.2),
        ("PROT:C12:TYR", "LIG:X3", -2.5),
        ("PROT:D88:VAL", "LIG:X4", -2.0),
        ("PROT:E31:HIS", "LIG:X5", -1.5),
        ("PROT:F19:SER", "LIG:X6", -1.2),
    ]
    methods = ["METHOD_A", "METHOD_B"]
    states = ["STATE_REF", "STATE_ALT"]

    rows = []
    for state in states:
        for method in methods:
            method_offset = -0.4 if method == "METHOD_B" else 0.0
            for res_1, res_2, base in pairs:
                perturb = 0.0
                if state == "STATE_ALT" and res_1 == "PROT:C12:TYR":
                    perturb = +1.3
                if method == "METHOD_B" and res_1 == "PROT:A45:ASP":
                    perturb += -0.8
                noise = ar1(n, rho=0.65, sigma=0.35, rng=rng)
                for t in range(n):
                    rows.append(
                        {
                            "sample_id": f"snap_{t:04d}",
                            "frame_id": t,
                            "system_id": "toy_complex",
                            "state_id": state,
                            "method_id": method,
                            "res_1": res_1,
                            "res_2": res_2,
                            "component": "total",
                            "energy_total": base + method_offset + perturb + noise[t],
                        }
                    )
    df = pd.DataFrame(rows)
    outdir = Path(__file__).resolve().parent
    df.to_csv(outdir / "energies.csv", index=False)
    meta = {
        "schema_version": "0.1",
        "energy_unit": "kcal/mol",
        "sign_convention": "negative_is_stabilizing",
        "snapshots_shared_across_methods": True,
        "snapshot_definition": "Synthetic sample_id values are shared physical snapshots across methods.",
        "provenance": {"METHOD_A": "synthetic AR(1)", "METHOD_B": "synthetic AR(1) with offsets"},
    }
    with (outdir / "metadata.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, sort_keys=False)


if __name__ == "__main__":
    main()
