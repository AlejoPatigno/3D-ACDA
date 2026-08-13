# Design: Phase 18 Scientific Freeze

## Technical approach

Use a documentation-only protocol layer around the existing protected experiment/evaluation contracts. The layer resolves and records scientific values, matrix identities, immutable artifact hashes, synthetic feasibility observations, resource placeholders, and a fail-closed authorization manifest. It does not add a runner or alter runtime behavior.

```text
canonical evidence -> resolution ledger -> matrix/schema
                                      -> provenance/budget
                                      -> real-run gate
```

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Method inventory | Seven Phase 15 protected IDs only | Prevents unreviewed aliases and historical helper names from becoming methods. |
| Matrix | Parser IDs `adni_to_oasis`/`oasis_to_adni`, folds `0..4`, seed `42`, 70 training rows plus 70 linked `last` projections | Matches repository contracts, forbids selective-fold evidence, and guarantees exactly one training invocation per method/direction/fold/seed. |
| Lambda discrepancy | Remains blocking and rejects authorization | Primary `1.0` and later helper/manuscript `0.2` cannot be resolved by target results; the matrix and real-run gate stay blocked until an authoritative decision hash exists. |
| Ablations | Inventory evidence only; publication subset unresolved | Phase 17 synthetic approval does not authorize publication inclusion. |
| Feasibility | Synthetic faithful shapes/contracts only | Gives contract evidence without real data or publication claims; synthetic timing/resource observations cannot resolve real fields. |
| Authorization | Hash-bound and fail-closed | Missing science, provenance, privacy, budget, or review evidence stops before data access. |

## Data flow and contracts

The resolution ledger classifies every value as `canonical_fixed`, `manually_selected_pre_run`, `engineering_only`, or `unresolved_blocking`. The matrix compiler emits one training row per method/direction/fold/seed and one linked checkpoint-projection row, with exactly one training invocation per cell, and never emits `COMPLETED` during planning. Provenance binds split/assignment, atlas/ROI, concept/Jacobian, model/config, environment, command, canonicalization conformance, and approval hashes. Target manifests are hash-verified before a content-level intersection check; target adaptation accepts only the four approved fields and target evaluation is disjoint monitoring.

A future implementation may consume the gate only after independent specification review and explicit human authorization. Resume requires the complete identity to match. Failures remain visible and cannot be silently skipped, retried, or overwritten.

## File changes

- Create/update the owned Phase 18 specification files listed by the request.
- Create/update this OpenSpec proposal, design, tasks, state, and `specs/experiment-freeze/spec.md`.
- Do not modify runtime code, configs, tests, docs outside the owned specification set, `.git`, or data.

## Verification and rollout

Verification for this change is artifact consistency and cross-document state checking only. No tests, feasibility probes, training, evaluation, publication analysis, or native review lifecycle command is run. After independent approval, future implementation must remain separable into schema/provenance, synthetic feasibility, and authorization/CLI slices.

## Open questions

- Which authoritative decision resolves `lambda_proto`?
- Which publication ablation subset is selected?
- Which real manifests, hardware observations, privacy record, command hash, and manuscript equations complete the gate?
