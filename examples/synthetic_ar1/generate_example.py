"""Generate a small synthetic DecompStat dataset with known AR(1) autocorrelation.

The data are artificial and intended for tests/tutorials only. They contain two methods
(MM_MM and SQM_MM), two states (WT and B16R), and a small set of residue pairs. The SQM_MM
method has a known offset relative to MM_MM for selected pairs, and B16R perturbs one hotspot.
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
        ("INS:B24:PHE", "IR:L1:ASN15", -4.0),
        ("INS:B25:PHE", "IR:L1:PHE39", -3.2),
        ("INS:B16:TYR", "IR:FNIII:ASP496", -2.5),
        ("INS:A3:VAL", "IR:ACT:ASN711", -2.0),
        ("INS:B10:HIS", "IR:L1:ARG65", -1.5),
        ("INS:B9:SER", "IR:L1:LYS40", -1.2),
    ]
    methods = ["MM_MM", "SQM_MM"]
    states = ["WT", "B16R"]

    rows = []
    for state in states:
        for method in methods:
            method_offset = -0.4 if method == "SQM_MM" else 0.0
            for res_1, res_2, base in pairs:
                perturb = 0.0
                if state == "B16R" and res_1 == "INS:B16:TYR":
                    perturb = +1.3  # weakened interaction in mutant
                if method == "SQM_MM" and res_1 == "INS:B24:PHE":
                    perturb += -0.8  # known protocol disagreement/hotspot strengthening
                noise = ar1(n, rho=0.65, sigma=0.35, rng=rng)
                for t in range(n):
                    rows.append(
                        {
                            "sample_id": f"snap_{t:04d}",
                            "frame_id": t,
                            "system_id": "insulin_ir_synthetic",
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
        "provenance": {"MM_MM": "synthetic AR(1)", "SQM_MM": "synthetic AR(1) with offsets"},
    }
    with (outdir / "metadata.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, sort_keys=False)


if __name__ == "__main__":
    main()
