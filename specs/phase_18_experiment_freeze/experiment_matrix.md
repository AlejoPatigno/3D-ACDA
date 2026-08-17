# Phase 18 Deterministic Experiment Matrix

## Matrix status

The matrix is a planning-only, authorization-blocked artifact. It contains no completed run, real-data output, or publication metric. All selected values were pre-run decisions; target outcomes were not inspected.

## Core dimensions

| Axis | Values | Class | Rule |
|---|---|---|---|
| Method | `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, `faster_snn` | `RESOLVED_CANONICAL` | Exact protected inventory and order. |
| Direction | `adni_to_oasis`, `oasis_to_adni` | `RESOLVED_CANONICAL` | Parser-bound lowercase IDs; display aliases are rejected. |
| Fold | `0,1,2,3,4` | `RESOLVED_CANONICAL` | Complete five-fold policy. |
| Seed | `42,43,44` | `RESOLVED_PRE_RUN_HUMAN` | Source split and target partition seed `42`; predeclared; posthoc selection forbidden. |
| Primary checkpoint | `best_source_f1` | `RESOLVED_PRE_RUN_HUMAN` | Source-validation macro-F1 only, no tie-breaker. |
| Sensitivity checkpoint | `last` | `RESOLVED_CANONICAL` | Separate linked projection; never retrains. |

## Counts and order

The core matrix contains exactly:

- `210` training rows (`7 × 2 × 5 × 3`);
- `210` checkpoint-projection rows;
- `420` total rows.

Canonical order is method, direction, seed ascending, fold ascending, then the linked `best_source_f1` training row and `last` projection. A projection has `training_invocation: false` and an exact `parent_training_id`; it cannot schedule another training invocation.

## Separate ablation section

Ablations are classification/planning rows outside the core matrix and do not train in Phase 18:

| Classification | IDs | Training-cell count | Projection-cell count |
|---|---|---:|---:|
| Primary | `no_proto`, `no_pl`, `no_concept`, `no_anat` | `120` | `120` |
| Supplementary | `no_cons`, `mean_pool` | `60` | `60` |
| Excluded | `no_domain_adaptation`, `no_ctx_encoder`, `full`, `identity_ctx` | `120` excluded | `0` |

Ablation planning records have `section: ablations`, `planning_only: true`, and `training_invocation: false`. They do not add rows to the 420-row core identity and do not carry metrics.

## Seed policy payload

```yaml
resolved_seed_policy:
  resolved: true
  seeds: [42, 43, 44]
  source: pre_run_human_decision
  source_split_random_state: 42
  target_partition_seed: 42
  predeclared: true
  posthoc_selection_forbidden: true
```

## Row invariants

Every row has the complete ordered identity fields, explicit assignment/config/artifact placeholders, a planning-only state, and `completion_allowed: false`. Missing rows, duplicate training cells, orphan projections, unsupported methods, aliases, completed states, or mismatched seed policy invalidate the matrix. No target outcome may select a method, seed, fold, checkpoint, ablation, or hyperparameter.
