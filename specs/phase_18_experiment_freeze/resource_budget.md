# Phase 18 — Resource Budget

## Budget status

No hardware observation or real run was performed. All unobserved resource values are explicit `unresolved_blocking` placeholders. The cell counts below are deterministic planning arithmetic and `engineering_only`; they are not duration or capacity claims.

## Workload identity

| Quantity | Value | Class | Source |
|---|---:|---|---|
| Core methods | 7 | canonical_fixed | Phase 15 inventory/config |
| Directions | 2 | canonical_fixed | repository invariant |
| Folds | 5 (`0..4`) | canonical_fixed | experiment/evaluation configs |
| Seeds | 1 (`42`) | canonical_fixed evidence; pre-run approval required | repository configs |
| Primary training cells | 70 | engineering_only | `7×2×5×1` |
| Sensitivity projections | 70 | engineering_only | one `last` projection per primary cell |
| Potential publication ablation cells | 60 | engineering_only, inactive | `6×2×5×1`; subset unresolved |
| Real data concurrency | 1 sequential cell | engineering_only proposal | conservative default; not a measured hardware result |

## Conservative and nominal scenarios

| Resource | Conservative placeholder | Nominal placeholder | Required evidence before authorization |
|---|---|---|---|
| Device type | `UNRESOLVED` | `UNRESOLVED` | observed approved device and software backend |
| GPU VRAM | `UNRESOLVED` | `UNRESOLVED` | synthetic faithful-shape peak-memory record |
| Host RAM | `UNRESOLVED` | `UNRESOLVED` | synthetic observation plus OS/runtime margin |
| Storage per cell | `UNRESOLVED` | `UNRESOLVED` | measured checkpoint/history/prediction/artifact sizes |
| Total storage | `UNRESOLVED` | `UNRESOLVED` | measured per-cell size × approved cell count + staging margin |
| Wall time per primary cell | `UNRESOLVED` | `UNRESOLVED` | real-data pilot/production observation or separately approved operational evidence; synthetic timing is diagnostic only and cannot resolve this field |
| Total wall time | `UNRESOLVED` | `UNRESOLVED` | sum of approved real per-cell observations; no synthetic timing or optimistic parallelism assumption |
| Workers | `UNRESOLVED` | `UNRESOLVED` | hardware/data-loader observation; configs contain method-specific values |
| Retry allowance | `UNRESOLVED` | `UNRESOLVED` | maintainer-selected failure policy; no automatic retry is assumed |
| Checkpoint interval | repository-configured where applicable; method-specific approval required | same | resolved training config and hash |

## Budget formulas

The authorization manifest MUST carry formulas with resolved operands, not fabricated estimates:

```text
primary_cell_count = methods × directions × folds × seeds
primary_storage = primary_cell_count × measured_storage_per_cell + staging_margin
primary_wall_time = sum(measured_or_approved_wall_time_per_cell)
```

If ablations are selected, their cell count and budget are added only after the exact subset and all inherited values are approved. No budget may be inferred from synthetic fixture runtime or from Phase 17's `1178 passed` test duration. Synthetic feasibility may record shape/contract timing and peak memory as `engineering_only`, but it MUST NOT populate, resolve, or authorize any real wall-time, memory, storage, worker, concurrency, or retry field.

## Operational policy

- Use sequential execution unless a separate concurrency decision is recorded; parallel execution is not implied by the matrix.
- Preserve `overwrite=false` and identity-bound resume behavior.
- A failed or interrupted cell remains visible and does not free the budget by being omitted.
- A retry requires the same identity or a new approved matrix/configuration identity; changing resources, batch size, epochs, or coefficients creates a new decision requirement.
- OOM, timeout, storage exhaustion, or repeated infrastructure failure blocks the affected cell and escalates budget approval; it does not trigger target-guided tuning.

## Current gate

`device`, memory, storage, wall-time, retry, and complete budget approval are `unresolved_blocking`. Therefore the real-run gate remains closed.

## Machine-readable planning payload

```yaml
schema_version: phase18.resource-budget.v1
mode: synthetic_only_planning
phase_18_authorized: true
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
evidence_types:
  - measured_synthetic
  - extrapolated_from_synthetic
  - not_recorded
  - blocked
workload:
  methods: 7
  directions: 2
  folds: 5
  seeds: 1
  primary_cell_count: 70
  sensitivity_projection_count: 70
formulas:
  primary_cell_count: "7 × 2 × 5 × 1 = 70"
  primary_storage: "70 × measured_storage_per_cell + staging_margin"
  primary_wall_time: "sum(measured_or_approved_wall_time_per_cell)"
fields:
  device_type:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: observed approved device and software backend
    evidence_type: blocked
    status: unresolved_blocking
  gpu_vram:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: synthetic faithful-shape peak-memory record plus real approval
    evidence_type: blocked
    status: unresolved_blocking
  host_ram:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: synthetic observation plus OS/runtime margin and real approval
    evidence_type: blocked
    status: unresolved_blocking
  storage_per_cell:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: measured real checkpoint/history/prediction/artifact sizes
    evidence_type: blocked
    status: unresolved_blocking
  total_storage:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: measured per-cell size times approved cell count plus staging margin
    evidence_type: blocked
    status: unresolved_blocking
  wall_time_per_primary_cell:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: real-data pilot or separately approved operational evidence
    evidence_type: extrapolated_from_synthetic
    status: unresolved_blocking
  total_wall_time:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: sum of approved real per-cell observations
    evidence_type: extrapolated_from_synthetic
    status: unresolved_blocking
  workers:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: hardware and data-loader observation
    evidence_type: blocked
    status: unresolved_blocking
  retry_allowance:
    conservative: UNRESOLVED
    nominal: UNRESOLVED
    required_evidence: maintainer-selected failure policy
    evidence_type: blocked
    status: unresolved_blocking
  concurrency:
    conservative: "1 sequential cell"
    nominal: "1 sequential cell"
    required_evidence: separate concurrency decision
    evidence_type: not_recorded
    status: unresolved_blocking
real_budget_closed: false
closure_rejection: synthetic observations and planning arithmetic cannot resolve real resource fields
``` 

The payload is planning evidence only. Synthetic values never transition a real field out of `unresolved_blocking` and cannot authorize throughput, execution, publication, or Phase 19.
