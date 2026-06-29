# DecompStat canonical schema specification

This document defines the DecompStat v0.1 canonical input format.

The goal is to make snapshot-level interaction-energy and score analyses explicit,
reproducible, and safe against silent misalignment of methods, states, residue pairs,
and snapshots.

## 1. Canonical data table

Input data are stored as a long-format CSV table. Each row represents one computed or
measured value for one snapshot, one system/state/method group, one residue or
residue-pair entity, and one component.

### Required columns

| Column | Type after loading | Meaning |
|---|---:|---|
| sample_id | string | Identifier of the physical snapshot. This is the primary key for pairing across methods or states. |
| system_id | string | System identifier, for example receptor-ligand system, protein complex, or simulation system. |
| state_id | string | State identifier, for example WT, mutant, ligand state, protonation state, or scan variant. |
| method_id | string | Method or protocol identifier. |
| res_1 | string | First residue/entity identifier. For per-residue data, this may be the analyzed residue. |
| res_2 | string | Second residue/entity identifier. For per-residue data, this may be a fixed partner or placeholder. |
| energy_total | float | Numeric value to analyze. Units and sign convention are defined by metadata. |

### Optional columns

| Column | Type after loading | Meaning |
|---|---:|---|
| frame_id | user-provided | Original frame identifier from the source workflow. Not used as the primary pairing key. |
| replica_id | string | Replica or trajectory identifier. |
| time_ps | numeric | Snapshot time in picoseconds, if available. |
| energy_unit | string | Optional row-level unit annotation. If present, it must not conflict with metadata. |
| component | string | Energy or score component. Missing values are normalized to total. |

## 2. Identifier rules

All identifier columns used for grouping or pairing are normalized to strings during
loading. This prevents accidental mismatches such as 001 versus 1, or mixed integer
and string keys.

sample_id is the physical snapshot key. Optional columns such as frame_id,
replica_id, and time_ps are provenance fields and must not replace sample_id in
paired comparisons.

res_1 and res_2 are ordered, literal identifiers. DecompStat v0.1 does not
canonicalize residue-pair orientation automatically: (A, B) and (B, A) are
different keys unless the input workflow normalizes them before loading.

## 3. Uniqueness rule

After normalization, this key must be unique:

system_id, state_id, method_id, sample_id, res_1, res_2, component

Duplicate rows with the same key are rejected.

## 4. Metadata sidecar

Each dataset should be accompanied by a JSON or YAML metadata sidecar.

Supported metadata fields:

| Field | Type | Default | Meaning |
|---|---:|---|---|
| schema_version | string | 0.1 | DecompStat schema version. |
| energy_unit | string | kcal/mol | Dataset-level unit. Supported values: kcal/mol, kJ/mol. |
| sign_convention | string | negative_is_stabilizing | Supported values: negative_is_stabilizing, positive_is_stabilizing. |
| snapshots_shared_across_methods | boolean | false | User assertion that shared sample_id values denote the same physical snapshots across compared methods. |
| snapshot_definition | string | empty | Human-readable definition of how sample_id values were assigned. |
| provenance | object | empty | Free-form provenance information. |

Unknown metadata fields are rejected.

## 5. Unit and sign checks

If the optional energy_unit column is present in the data table, it must contain at
most one non-missing value. That value must match metadata energy_unit.

The sign convention is dataset-level metadata. DecompStat does not infer physical
meaning from the sign of energy_total; it uses the declared metadata.

## 6. Snapshot-pairing assertion

Paired comparisons require snapshots_shared_across_methods: true in metadata. The
software can check whether sample_id keys match, but only the user can assert that
matching sample_id values correspond to the same physical snapshots.

## 7. Validation failures

Validation fails if:

- a required column is missing;
- the table is empty;
- required columns contain missing values;
- energy_total contains NaN or infinite values;
- the uniqueness rule is violated;
- row-level energy_unit conflicts with metadata;
- paired comparison is requested without the snapshot-sharing assertion.

## 8. Scope

The canonical schema is independent of any particular molecular simulation package,
quantum-chemical program, spreadsheet layout, or biological system. Project-specific
converters belong in examples or external reproducibility workflows. They are not part
of the core DecompStat schema.
