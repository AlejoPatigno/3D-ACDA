# Phase 18 — Real-Run Authorization Gate

## Current decision

The gate is **CLOSED**. Phase 18 protocol planning is authorized, but real execution and publication are not. Current values are:

```yaml
phase_18_authorized: true
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
gate_result: blocked
```

No data loader, training loop, evaluator, or publication writer may bypass this state.

## Required authorization record

A future real-run request MUST provide one immutable, independently reviewed gate manifest containing:

```yaml
schema_version: phase18.real-run-gate.v1
phase_18_authorized: true
real_execution_authorized: true
publication_authorized: false  # remains false unless separately approved
phase_19_forbidden: true
scientific_resolution_hash: <resolved value ledger hash; lambda_proto must not be unresolved>
method_parameter_ledger_hash: <checked-in CORAL/MMD/CDAN parameter ledger hash>
canonicalization_conformance_hash: <phase18.canonical-json.v1 vectors and implementation hash>
matrix_hash: <complete ordered matrix hash>
method_inventory_hash: <seven-method inventory hash>
seed_policy_hash: <approved pre-run seed policy hash>
split_manifest_hashes: {ADNI: <sha256>, OASIS: <sha256>}
assignment_hashes:
  source: <sha256>
  target_adaptation: <sha256>
  target_evaluation: <sha256>
assignment_manifest_contents:
  target_adaptation_subject_hashes: <hash-verified parsed set>
  target_evaluation_subject_hashes: <hash-verified parsed set>
  required_intersection: empty
  aggregate_hashes_alone_are_insufficient: true
artifact_hashes:
  atlas: <sha256>
  roi_order: <sha256>
  roi_masks: <sha256>
  concept_normalizer: <sha256>
  concept_targets: <sha256>
  jacobians: <sha256>
configuration_hash: <sha256>
code_revision: <immutable revision>
environment_hash: <sha256>
command_hash: <sha256>
privacy_data_access_record_hash: <sha256>
resource_budget_hash: <sha256>
feasibility_observation_hash: <sha256>
independent_review_hash: <sha256>
human_authorization_hash: <sha256>
```

Any missing, null, conflicting, stale, or mismatched field is `unresolved_blocking`. Publication authorization is a separate gate and cannot be inferred from real-run authorization.

## Preflight order

1. Parse exact configuration and selectors.
2. Verify the gate manifest and every referenced hash.
3. Verify the complete matrix: canonical parser IDs `adni_to_oasis` and `oasis_to_adni`, folds `0..4`, approved seed policy, exactly one training invocation per method/direction/fold/seed cell, and one `last` projection linked by `parent_training_id`; no missing/duplicate/orphan rows.
4. Verify exact checked-in CORAL/MMD/CDAN parameter fields through loader validation; missing, null, malformed, or invented defaults fail closed.
5. Verify hash-verified target-adaptation and target-evaluation manifest contents, compute their subject-identity intersection, and require it to be empty. Aggregate assignment hashes alone are insufficient. Verify the target-adaptation four-key firewall.
6. Verify immutable atlas/ROI/concept/Jacobian/split artifacts without regeneration.
7. Verify the `phase18.canonical-json.v1` implementation and authoritative conformance vectors, including numeric, negative-zero, Unicode, and separator cases.
8. Verify device/resource budget and privacy/data access; synthetic timing or memory observations MUST NOT resolve real resource fields.
9. Verify output root is empty/approved for the exact identity and resume is either absent or identity-matching.
10. Emit an auditable preflight result.
11. Only after all checks pass may a future command open real inputs.

A failure at any step stops before data access and records a structured reason.

## CLI contract for a future implementation

The implementation must preserve existing planning conventions and expose, at minimum:

- `--config PATH` for the resolved experiment configuration;
- exact `--method` or an explicit approved all-methods selector;
- `--direction` or `--both-directions`;
- `--fold` or `--all-folds`;
- `--seed` or the exact approved seed set;
- `--artifact-index PATH`, split/assignment references, and `--output-root PATH`;
- `--dry-run` and `--validate-only`, which must not load real data or create runtime outputs;
- `--resume-from PATH`, restricted to one identity-matching cell;
- an explicit authorization-manifest input for real mode.

Existing repository command shapes in `scripts/train.py`, `scripts/run_ablations.py`, and `scripts/evaluate.py` are references, not permission to execute. No implicit default may turn a dry-run/validate-only request into a real run. Unknown names, unsupported aliases, non-canonical direction IDs, unresolved coefficients or method parameters, missing hashes, missing canonicalization vectors, target-label leakage, non-empty manifest intersections, and incomplete matrices must fail closed.

## Publication boundary

Real execution does not authorize publication metrics, manuscript tables, statistical comparisons, or conclusions. Those require a separate publication gate with an authoritative manuscript/statistical protocol and its own hash-bound approval. Phase 19 remains forbidden.

## Current blockers

`lambda_proto`, checked-in CORAL/MMD/CDAN parameters, publication ablation selection, canonicalization conformance evidence, real assignments/artifact hashes, content-level assignment disjointness, privacy/data access, hardware budget, command hash, independent approval, and human authorization are unresolved. The gate therefore remains `blocked`; no matrix or real-run authorization may be emitted while any one remains unresolved.
