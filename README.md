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


## Precomputed score summaries

DecompStat can also summarize already-computed snapshot-level scores, such as
mutation-level `ddg_score` values. In this mode, `energy_total` is treated as the
score itself. No WT-vs-mutant subtraction is performed.

Example command:

    decompstat score-summary examples/insulin_b16_manual/b16_manual_test.csv \
      examples/insulin_b16_manual/metadata.yaml \
      --group "method_id=SQM_MM_LEAP,component=ddg_score" \
      --threshold 0.5 \
      --out examples/insulin_b16_manual/score_summary.csv

The output reports the mean score, score spread, number and fraction of favourable
snapshots, and the rank by mean score. Use `--min-samples` to exclude incomplete
groups from ranking, for example when only mutations observed in all snapshots should
be compared.

## Excel mutation-score workbook conversion

A project-specific adapter is included for the insulin mutation-score workbook used in
the example. It converts wide snapshot blocks into the canonical long CSV format. The
adapter is separate from the canonical schema; users with other input formats can write
canonical CSV files directly.

Example command:

    decompstat convert-excel path/to/A8_A19_B16_B18_B24_B25_B26_TRAJ_1_TRAJ_2_TRAJ3.xlsx \
      --sheets A19,B16,B24,B25,B26 \
      --out examples/insulin_mutation_scores/insulin_mutation_scores.csv

The converted dataset can then be validated and summarized:

    decompstat validate examples/insulin_mutation_scores/insulin_mutation_scores.csv \
      examples/insulin_mutation_scores/metadata.yaml \
      --require-snapshot-assertion

    decompstat score-summary examples/insulin_mutation_scores/insulin_mutation_scores.csv \
      examples/insulin_mutation_scores/metadata.yaml \
      --group "method_id=SQM_MM_LEAP,component=ddg_score" \
      --threshold 0.5 \
      --min-samples 11 \
      --out examples/insulin_mutation_scores/score_summary_min11.csv

## Statistical scope

Uncertainty is estimated by moving-block bootstrap with block length derived from statistical
inefficiency. DecompStat introduces no new estimator. These estimates correct the nominal sample
size for serial correlation, but they do not replace adequate conformational sampling. For very
short or strongly autocorrelated series, output warnings should be treated seriously.

## Current status

This is a v0.1.0 scaffold intended for audit and iteration before any SoftwareX submission.
The first development priority is correctness of schema validation, snapshot pairing, and
sample-level bootstrap behavior.
