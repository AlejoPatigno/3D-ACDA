# Phase 18 — Freeze and Run Schema

## Schema identity

```yaml
schema_version: phase18.freeze.v1
hash_algorithm: sha256
canonicalization: phase18.canonical-json.v1
phase: 18
```

The schema describes records; it does not assert that any record exists or that a run is authorized.

## State vocabulary

| State | Meaning | Allowed now |
|---|---|---:|
| `PLANNED` | Complete intended row, not authorized or started | yes, future |
| `BLOCKED` | Missing approval, value, provenance, resource, or integrity evidence | yes, current |
| `READY_FOR_AUTHORIZATION` | Independent review passed; gate manifest still awaits human authorization | future |
| `AUTHORIZED` | Gate manifest and human authorization are valid | future only |
| `RUNNING` | Authorized cell is executing | future only |
| `RETRY_REQUIRED` | Interrupted/transient failure with identity preserved | future only |
| `FAILED` | Terminal cell failure recorded with evidence | future only |
| `COMPLETED` | Later authorized run and independent verification fully passed | forbidden in this Phase 18 planning matrix |

A row MUST NOT be deleted to hide a failure, and a missing/duplicate row invalidates the matrix. The selected pre-run seed policy is `[42,43,44]`, with source split random state `42`, target partition seed `42`, and posthoc selection forbidden. The schema accepts an explicit resolved seed policy rather than hard-coding seed `42`.

## Freeze record

```yaml
FreezeRecord:
  schema_version: phase18.freeze.v1
  phase: 18
  status: blocked_planning
  phase_18_authorized: true
  real_execution_authorized: false
  publication_authorized: false
  phase_19_forbidden: true
  scientific_resolution_hash: sha256-or-unresolved
  matrix_hash: sha256-or-unresolved
  provenance_freeze_hash: sha256-or-unresolved
  feasibility_hash: sha256-or-unresolved
  resource_budget_hash: sha256-or-unresolved
  independent_review_hash: sha256-or-unresolved
  human_authorization_hash: sha256-or-unresolved
```

## Matrix row

```yaml
MatrixRow:
  matrix_id: sha256
  row_kind: training | checkpoint_projection
  parent_training_id: null for training; exact training row ID for checkpoint_projection
  training_invocation: true for training; false for checkpoint_projection
  method_id: source_only | coral | mmd | cdan | prototype_pseudo | aagn | faster_snn
  public_method_name: string
  direction: adni_to_oasis | oasis_to_adni
  source_cohort: ADNI | OASIS
  target_cohort: ADNI | OASIS
  fold: 0 | 1 | 2 | 3 | 4
  seed: 42 | 43 | 44
  checkpoint_policy: best_source_f1 for training | last for checkpoint_projection
  resolved_config_hash: sha256-or-unresolved
  split_assignment_hash: sha256-or-unresolved
  target_adaptation_assignment_hash: sha256-or-unresolved
  target_evaluation_assignment_hash: sha256-or-unresolved
  immutable_artifacts_hash: sha256-or-unresolved
  state: PLANNED | BLOCKED | READY_FOR_AUTHORIZATION | AUTHORIZED | RUNNING | RETRY_REQUIRED | FAILED
  completion_allowed: false
  blocked_reasons: [string]
```

## Target role schema

```yaml
TargetAdaptationBatch:
  allowed_keys: [x, subject_id, subject_hash, cohort]
  labels_present: false
TargetEvaluationRecord:
  role: target_evaluation
  target_monitoring_label: MONITORING ONLY — NOT A TRAINING LOSS
  training_loss_usage: forbidden
  selection_usage: forbidden
```

Extra keys are rejected rather than dropped. Assignment identity is separate for adaptation and evaluation. The exact manifest bytes are hash-verified before parsing, and the parsed subject-identity sets MUST have an empty intersection; aggregate assignment hashes alone are insufficient.

## Artifact roles

A future cell may contain, subject to authorization and existing repository output contracts:

- resolved configuration and method identity;
- atomic `checkpoint_last` and `checkpoint_best_source_f1` plus epoch checkpoints as configured;
- fixed-epoch history with raw/weighted components and monitoring namespace;
- source-validation and target-monitoring predictions;
- reproducibility metadata;
- equivalence/disposition manifest;
- artifact index with exact byte hashes.

No artifact may contain MRI data in a checkpoint, target-adaptation diagnosis labels, raw subject identifiers in public metadata, or a publication result before a publication gate.

## Failure vocabulary

Structured reasons include `authorization_blocked`, `unresolved_scientific_value`, `unresolved_method_parameter`, `non_canonical_direction`, `incomplete_matrix`, `missing_assignment`, `overlapping_assignments`, `missing_immutable_artifact`, `target_label_firewall_violation`, `provenance_conflict`, `canonicalization_unresolved`, `hash_mismatch`, `shape_mismatch`, `non_finite_value`, `resource_budget_unresolved`, `interrupted`, `runtime_failure`, `storage_failure`, `resume_identity_mismatch`, and `publication_not_authorized`. A missing, duplicate, or orphan `row_kind`/`parent_training_id` relationship is `incomplete_matrix`.

Failures are retained with evidence. Retry is never automatic when identity, configuration, resource assumptions, or scientific values change.
