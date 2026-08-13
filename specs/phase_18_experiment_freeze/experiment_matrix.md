# Phase 18 — Deterministic Experiment Matrix

## Matrix status

This is a planned, authorization-blocked matrix. It contains no completed run and no real-data output. Every future cell must be materialized with an explicit state; `COMPLETED` is prohibited until a separate authorized execution and verification phase.

## Frozen dimensions

| Axis | Values | Class | Rule |
|---|---|---|---|
| Method | `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, `faster_snn` | canonical_fixed | Exact Phase 15 protected inventory and order. |
| Direction | `adni_to_oasis`, `oasis_to_adni` | canonical_fixed parser identifiers | Both directions are mandatory and never pooled. These exact lowercase IDs are parser-bound; display labels `ADNI -> OASIS` and `OASIS -> ADNI` are not accepted as row identifiers. |
| Fold | `0, 1, 2, 3, 4` | canonical_fixed | Complete five-fold policy; no selective-fold shortcut. |
| Seed | `42` | canonical_fixed repository evidence; pre-run approval required | No additional seed is invented. |
| Primary checkpoint | `best_source_f1` | canonical_fixed | Selected only by source-validation macro-F1. |
| Sensitivity checkpoint | `last` | canonical_fixed evaluation projection | Separate analysis; never pooled with primary. |
| Class order | `CN, MCI, AD` = `0,1,2` | canonical_fixed | Fixed everywhere. |

## Cell counts and order

The matrix has 70 planned training rows and 70 planned checkpoint-projection rows. There MUST be exactly one training invocation for each method/direction/fold/seed cell (`7 × 2 × 5 × 1 = 70`), and exactly one `last` projection row attached to each training row. These are planning counts, not runtime observations; a projection row MUST NOT schedule another training invocation.

Canonical row ordering is:

1. method order shown above;
2. parser direction ID `adni_to_oasis`, then `oasis_to_adni`;
3. seed ascending;
4. fold ascending;
5. checkpoint `best_source_f1`, then `last`.

## Publication ablation boundary

The Phase 17 candidate evidence is retained outside the core matrix. The potential ablation dimensions would be six candidates × two directions × five folds × one seed = 60 cells, but the publication subset is `unresolved_blocking`. No ablation row is activated until a human selects the exact subset and resolves inherited coefficients, including `lambda_proto`.

## Matrix row schema

Every row MUST contain the following fields:

```yaml
matrix_schema: phase18.matrix.v1
row:
  matrix_id: <hash of ordered matrix definition>
  row_kind: training | checkpoint_projection
  parent_training_id: null for training; exact training row ID for checkpoint_projection
  training_invocation: true for training; false for checkpoint_projection
  method_id: <exact protected ID>
  public_method_name: <canonical display name>
  source_cohort: ADNI | OASIS
  target_cohort: ADNI | OASIS
  direction: adni_to_oasis | oasis_to_adni
  fold: 0..4
  seed: 42
  checkpoint_policy: best_source_f1 for training | last for checkpoint_projection
  split_assignment_hash: <required before authorization>
  target_adaptation_assignment_hash: <required before authorization>
  target_evaluation_assignment_hash: <required before authorization>
  resolved_config_hash: <required before authorization>
  artifact_identity_hash: <required before authorization>
  state: PLANNED | BLOCKED | READY_FOR_AUTHORIZATION | AUTHORIZED | RUNNING | RETRY_REQUIRED | FAILED | COMPLETED
  completion_allowed: false
  blocked_reasons: [<structured reasons>]
```

At the current phase every row has `state: BLOCKED` because real execution is false and the freeze has unresolved authorization/provenance decisions. A future approved but not started row may use `PLANNED` or `READY_FOR_AUTHORIZATION`; neither means a result exists.

## Cell transition rules

- `BLOCKED -> PLANNED` requires resolution of the named scientific/provenance blocker.
- `PLANNED -> READY_FOR_AUTHORIZATION` requires complete row identity and independent specification approval.
- `READY_FOR_AUTHORIZATION -> AUTHORIZED` requires the real-run gate and human approval.
- `AUTHORIZED -> RUNNING` occurs only after preflight passes without opening a non-authorized data path.
- `RUNNING -> RETRY_REQUIRED` is allowed only for an interrupted/transient failure with intact identity.
- `RUNNING -> FAILED` records a terminal failure and evidence; it is never omitted from summaries.
- `RUNNING -> COMPLETED` is not available to this specification action and requires later authorized verification.
- Hash drift, assignment overlap, target-label leakage, or artifact corruption transitions to `BLOCKED`/`FAILED`, never automatic repair.

## Matrix invariants

No target outcome may choose a method, fold, seed, checkpoint, ablation, or hyperparameter. Direction identifiers MUST be validated against the canonical lowercase parser enum; unknown, uppercase, display-form, or alias values are rejected, never silently remapped. Target adaptation and evaluation assignments are disjoint by content-level intersection checks over hash-verified manifests; aggregate assignment hashes alone are insufficient. Every training row has exactly one invocation per method/direction/fold/seed cell, and every checkpoint-projection row has `row_kind: checkpoint_projection`, `training_invocation: false`, and a valid `parent_training_id`. Missing rows, duplicate training rows, orphan projections, aliases, or unsupported methods invalidate the matrix rather than shrinking it.
