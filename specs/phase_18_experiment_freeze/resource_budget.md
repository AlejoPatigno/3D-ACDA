# Phase 18 — Resource Budget

## Final budget status

**Real resources are externally blocked.** No hardware observation or real run was performed. Planning arithmetic is deterministic and `ENGINEERING_ONLY`; it is not a duration, capacity, memory, storage, or throughput claim.

## Workload identity

| Quantity | Value | Class | Source |
|---|---:|---|---|
| Core methods | 7 | `canonical_fixed` | Phase 18 matrix/configuration |
| Directions | 2 | `canonical_fixed` | Repository invariant |
| Folds | 5 (`0..4`) | `canonical_fixed` | Experiment contract |
| Seeds | 3 (`42,43,44`) | `RESOLVED_PRE_RUN_HUMAN` | Maintainer pre-run decision |
| Primary training cells | 210 | `ENGINEERING_ONLY` | `7×2×5×3` |
| Sensitivity projections | 210 | `ENGINEERING_ONLY` | One non-training `last` projection per primary cell |
| Primary ablation cells | 120 | `ENGINEERING_ONLY`, selected pre-run | `4×2×5×3` |
| Supplementary ablation cells | 60 | `ENGINEERING_ONLY`, selected pre-run | `2×2×5×3` |
| Excluded ablation cells | 120 | `ENGINEERING_ONLY`, excluded | `4×2×5×3` |

The ablation counts are planning cells under three seeds; they are not part of the 420-row core matrix and no ablation row is executed here.

## Externally blocked fields

Device type, GPU VRAM, host RAM, storage per cell, total storage, wall time, workers, retry allowance, concurrency approval, and complete budget closure remain `BLOCKED_EXTERNAL_PROVENANCE`/`BLOCKED_RESOURCES`. Required evidence is an approved hardware observation, faithful-shape resource record, measured real-data storage/timing, and a maintainer-approved failure/retry policy.

Synthetic contract-level observations cannot resolve real resources. They must not populate or authorize any real wall-time, memory, storage, worker, concurrency, retry, or throughput field.

## Budget formulas

```text
primary_cell_count = methods × directions × folds × seeds = 7 × 2 × 5 × 3 = 210
primary_storage = primary_cell_count × measured_storage_per_cell + staging_margin
primary_wall_time = sum(measured_or_approved_wall_time_per_cell)
primary_ablation_cells = 4 × 2 × 5 × 3 = 120
supplementary_ablation_cells = 2 × 2 × 5 × 3 = 60
excluded_ablation_cells = 4 × 2 × 5 × 3 = 120
```

No synthetic fixture runtime, optimistic parallelism, timeout assumption, or omitted failed cell may close the budget. Sequential execution remains the planning default until separately approved.

## Machine-readable planning payload

```yaml
schema_version: phase18.resource-budget.v1
mode: synthetic_only_planning
phase_18_authorized: true
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
status: BLOCKED_EXTERNAL_RESOURCES
workload:
  methods: 7
  directions: 2
  folds: 5
  seeds: 3
  primary_cell_count: 210
  sensitivity_projection_count: 210
  primary_ablation_cells: 120
  supplementary_ablation_cells: 60
  excluded_ablation_cells: 120
real_budget_closed: false
real_resources_external_blocker: true
```

The real-run gate remains closed.
