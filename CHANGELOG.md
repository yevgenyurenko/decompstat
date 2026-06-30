# Changelog

## v0.1.0

Initial frozen schema/statistics release.

### Added

- Canonical long-format schema for paired decomposition tables.
- Metadata sidecar with unit, sign convention, provenance, and snapshot-pairing assertion.
- Runtime schema validation:
  - required columns
  - empty table
  - NaN / infinite `energy_total`
  - empty identifier strings
  - duplicate primary keys
  - row-level unit conflicts
  - missing snapshot-sharing assertion for paired comparison
- Paired comparison using shared `sample_id`, residue-pair, and component keys.
- Explicit paired-overlap coverage in compare output:
  - `n_pair_keys_ref`
  - `n_pair_keys_target`
  - `n_pair_keys_common`
  - `n_pair_keys_dropped_from_ref`
  - `n_pair_keys_dropped_from_target`
- Autocorrelation-aware moving-block bootstrap uncertainty:
  - statistical inefficiency `g`
  - effective sample size `n_eff`
  - block length
  - warning flags
- Rank-stability analysis with bootstrap top-k probabilities.
- Rank-agreement summary.
- Precomputed score-summary command.
- Neutral synthetic AR(1) cross-method residue-pair example.
- Optional project-specific Excel conversion script outside the importable package.
- GitHub Actions pytest matrix for Python 3.10, 3.11, and 3.12.

### Scope

DecompStat v0.1.0 does not compute interaction energies, parse MD/QM output files,
read trajectories, repair structures, or predict binding affinity. It provides a
validated statistical comparison layer for already-computed canonical tables.
