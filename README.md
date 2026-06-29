# DecompStat

DecompStat is a small Python package for paired statistical comparison and rank-stability
analysis of already-computed residue-level or residue-pair interaction-energy decompositions.

It **does not** compute energies, parse MD/QM output files, read trajectories, repair PDB files,
or predict binding affinity. It consumes a canonical long-format table plus a metadata sidecar.

## Canonical input contract

Required CSV columns:

- `sample_id`: physical snapshot identity shared across methods being compared.
- `system_id`: broad molecular system/project label.
- `state_id`: biological/chemical state, such as `WT` or `B16R`.
- `method_id`: computational method/protocol, such as `MM_MM`, `SQM_MM`, or `MMGBSA`.
- `res_1`, `res_2`: residue or fragment identifiers.
- `energy_total`: energy value.

Optional columns include `frame_id`, `replica_id`, `time_ps`, `energy_unit`, and `component`.
If `component` is absent, it is treated as `total`.

The metadata sidecar records unit, sign convention, provenance, and the required assertion that
`sample_id` values denote the same physical snapshots across methods.

## Quickstart

```bash
pip install -e .
python examples/synthetic_ar1/generate_example.py

decompstat validate examples/synthetic_ar1/energies.csv examples/synthetic_ar1/metadata.yaml \
  --require-snapshot-assertion

decompstat compare examples/synthetic_ar1/energies.csv examples/synthetic_ar1/metadata.yaml \
  --ref "state_id=WT,method_id=MM_MM" \
  --target "state_id=WT,method_id=SQM_MM" \
  --out compare.csv --n-boot 300

decompstat rank-stability examples/synthetic_ar1/energies.csv examples/synthetic_ar1/metadata.yaml \
  --group "state_id=WT,method_id=SQM_MM" \
  --top-k 3 --out ranks.csv --n-boot 300
```

## Statistical scope

Uncertainty is estimated by moving-block bootstrap with block length derived from statistical
inefficiency. DecompStat introduces no new estimator. These estimates correct the nominal sample
size for serial correlation, but they do not replace adequate conformational sampling. For very
short or strongly autocorrelated series, output warnings should be treated seriously.

## Current status

This is a v0.1.0 scaffold intended for audit and iteration before any SoftwareX submission.
The first development priority is correctness of schema validation, snapshot pairing, and
sample-level bootstrap behavior.
