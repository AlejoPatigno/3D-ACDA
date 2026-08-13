# Phase 18 — Synthetic Feasibility Protocol

## Purpose and boundary

This protocol defines a future feasibility observation only. It is not executed by this action. It MUST use deterministic synthetic tensors and metadata with faithful repository shapes; it MUST NOT discover, open, copy, train on, or evaluate ADNI/OASIS data. It produces engineering evidence, not scientific performance or publication claims.

## Faithful shape contract

Synthetic fixtures derive unresolved spatial dimensions from the approved model/configuration at execution time rather than inventing a publication shape.

| Contract | Faithful synthetic shape/fields | Class |
|---|---|---|
| MRI input | `x: (B, 1, H, W, D)`, finite `float32` | canonical_fixed rank/channel; `H,W,D` supplied pre-run |
| Model feature map | `(B, 256, h, w, d)` under the configured encoder | canonical_fixed from model config; grid derived |
| ROI masks | `(102, h, w, d)`, ordered, non-empty, normalized | canonical_fixed shape/order; synthetic content engineering_only |
| Tokens | `(B, 102, 128)` | canonical_fixed model contract |
| Subject embedding | `z: (B, 128)` | canonical_fixed model contract |
| Concepts and immutable targets | `concepts`, `c_target`, `g_bar`: `(B, 102)` | canonical_fixed contract; synthetic values engineering_only |
| Diagnosis logits/probabilities | `(B, 3)` with `CN,MCI,AD` order | canonical_fixed contract |
| Target adaptation batch | exactly `x`, `subject_id`, `subject_hash`, `cohort` | canonical_fixed firewall |
| Target evaluation batch | separate monitoring-only records | canonical_fixed isolation |

The small Phase 17 fixture dimensions are permitted only as `engineering_only` lifecycle fixtures; they are not faithful publication dimensions and MUST NOT be used to estimate real resource needs.

## Protocol stages

1. **Resolve-only:** load the approved synthetic configuration, exact method IDs, directions, folds, seed policy, and schema; do not create a real-data path.
2. **Shape validation:** construct deterministic synthetic inputs for each method family and validate rank, dtype, finiteness, ROI order, class order, and output schemas.
3. **Objective validation:** exercise warm/full equation wiring without target diagnosis labels; verify warm adaptation components are zero and loss-ablation intervention metadata is explicit.
4. **Firewall validation:** submit the exact four-key target-adaptation batch and negative batches containing labels, probabilities, concept targets, Jacobians, or other artifacts; reject negatives before loss.
5. **Checkpoint/resume validation:** use synthetic interruption and matching resume identity; verify changed identity, hash drift, corruption, and duplicate-history cases fail closed.
6. **Provenance validation:** build synthetic manifests for assignments, immutable artifacts, configuration, code, environment, and command; verify canonical hashes and stable ordering.
7. **Observation:** record synthetic-run wall time, peak host/device memory if observable, storage bytes, worker count, device, software versions, and failure reason under an explicitly synthetic observation namespace. Missing observations are `not_recorded`, never zero. These observations are engineering diagnostics only and MUST NOT resolve or populate real-data resource fields.

## Determinism policy

Use seed `42` because it is the repository-wide configured seed (`canonical_fixed`); synthetic content must be generated from a local deterministic generator and must not access external randomness or network resources. The seed is not evidence that the real publication matrix is approved.

## Pass/fail rules

A feasibility attempt passes contract validation only when all requested synthetic cells validate, no forbidden target field is accepted, hashes are stable, checkpoint identity is strict, and all required observations are either recorded or explicitly `not_recorded`. It fails closed on shape mismatch, non-finite values, missing artifact identity, duplicate rows, target-label leakage, or accidental real-data access.

A pass does **not** establish real throughput, real wall time, real memory fit, storage capacity, worker/concurrency suitability, retry allowance, statistical validity, or publication readiness. Synthetic feasibility may validate shapes, schemas, loader contracts, firewall behavior, checkpoint identity, and canonicalization contracts only. It MUST NOT resolve any real timing or resource field; hardware-budget approval remains a separate gate.

## Required observation record

```yaml
schema_version: phase18.feasibility.v1
mode: synthetic_only
real_data_accessed: false
publication_metrics_present: false
seed: 42
matrix_identity_hash: <hash>
device: <recorded-or-not_recorded>
synthetic_wall_time_seconds: <recorded-or-not_recorded>
synthetic_peak_memory_bytes: <recorded-or-not_recorded>
synthetic_storage_bytes: <recorded-or-not_recorded>
synthetic_workers: <recorded-or-not_recorded>
real_resource_fields_resolved: false
contract_result: pass | fail | blocked
failure_reasons: []
```

No feasibility observation exists for this specification action.
