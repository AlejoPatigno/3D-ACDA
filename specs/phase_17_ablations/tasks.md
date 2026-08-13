# Phase 17 — Dependency-Ordered Implementation Tasks

## Execution rule

This task list is for a separately authorized implementation transaction. The current specification action does not execute any task below. **Exactly one agent owns each action.** Agents must not edit another action's files, spawn a second implementation thread, run real data, or modify Phase 18. The transaction controller must preserve existing Phase 16 cleanup changes and all protected method behavior.

Exclusive ownership means an agent may edit only the files named in its row. If a needed file is outside that row, stop and request a scope update rather than editing it.

## Ordered task table

| Order | Action | Dependency | Exactly one agent | Exclusive file ownership | Required result |
|---:|---|---|---|---|---|
| 1 | `P17-A1-contract-fixture` | None | `contract-agent` | `tests/phase_17/fixtures/` only | Create deterministic in-memory registry, approval, matrix, and artifact fixtures. No MRI or real-data fixture. |
| 2 | `P17-A2-registry` | P17-A1 | `registry-agent` | `src/pada3dacb/ablations/registry.py` only | Define exact candidate records, provenance, dispositions, aliases, and protected-method references. Reject unknown and unapproved entries. |
| 3 | `P17-A3-resolver` | P17-A2 | `resolver-agent` | `src/pada3dacb/ablations/resolver.py` only | Resolve one approved candidate and one intervention; enforce coefficients, architecture boundary, matrix completeness, and structured blocked errors. |
| 4 | `P17-A4-equivalence` | P17-A2 | `equivalence-agent` | `src/pada3dacb/ablations/equivalence.py` only | Implement explicit `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, `full`, and alias dispositions. No silent alias. |
| 5 | `P17-A5-composition` | P17-A3 | `composition-agent` | `src/pada3dacb/ablations/composition.py` only | Apply exactly one loss override or approved `mean_pool` aggregator replacement to current PADA-3DACB. No contextual patch or duplicate model. |
| 6 | `P17-A6-diagnostics` | P17-A5 | `diagnostics-agent` | `src/pada3dacb/ablations/diagnostics.py` only | Emit active/raw/weighted component diagnostics and prove inherited terms remain unchanged. |
| 7 | `P17-A7-output-schema` | P17-A3 | `output-agent` | `src/pada3dacb/ablations/output_schema.py` only | Validate checkpoint, history, prediction, and equivalence manifest shapes and required hash/loader fields. |
| 8 | `P17-A8-hash-identity` | P17-A3, P17-A7 | `identity-agent` | `src/pada3dacb/ablations/identity.py` only | Canonicalize JSON and compute all required SHA-256 identity hashes; reject mismatch. |
| 9 | `P17-A9-trainer-adapter` | P17-A5, P17-A6, P17-A8 | `trainer-adapter-agent` | `src/pada3dacb/ablations/trainer_adapter.py` only | Adapt the existing trainer once; pass resolved contract, target firewall, diagnostics, fixed epochs, source-only checkpoint selection, history, and resume state. Do not implement a second trainer. |
| 10 | `P17-A10-cli` | P17-A4, P17-A7, P17-A8, P17-A9 | `cli-agent` | `src/pada3dacb/ablations/cli.py` only | Add preflight/resolve/synthetic-smoke/resume boundaries. Real data remains authorization-gated. |
| 11 | `P17-A11-focused-registry-resolver-tests` | P17-A2, P17-A3, P17-A4 | `registry-test-agent` | `tests/phase_17/test_registry_resolver.py` only | Test exact IDs, approval requirement, alias rejection, coefficient discrepancy, one-intervention rule, architecture dispositions, and complete matrix validation. |
| 12 | `P17-A12-focused-composition-tests` | P17-A5, P17-A6 | `composition-test-agent` | `tests/phase_17/test_composition_diagnostics.py` only | Test each loss ablation changes exactly one full-stage weighted term; warm adaptation remains zero; `mean_pool` is uniform; no contextual field appears. |
| 13 | `P17-A13-firewall-tests` | P17-A9 | `firewall-test-agent` | `tests/phase_17/test_target_firewall.py` only | Test target adaptation accepts exactly `x`, `subject_id`, `subject_hash`, and `cohort`; rejects diagnosis/label/label_name/true_label/c_target/g_bar/diagnosis/stored probabilities/concept/Jacobian/artifact supervision fields; enforces disjoint monitoring assignments. |
| 14 | `P17-A14-output-hash-tests` | P17-A7, P17-A8 | `output-test-agent` | `tests/phase_17/test_output_identity.py` only | Test required schemas, stable hashes, changed model hash for pooling, unchanged model hash for loss-only ablations, and hard-fail mismatch. |
| 15 | `P17-A15-synthetic-lifecycle` | P17-A9, P17-A10, P17-A13, P17-A14 | `lifecycle-agent` | `tests/phase_17/test_synthetic_lifecycle.py` only | Run a deterministic synthetic one-warm/one-full lifecycle with no real data; test checkpoint creation, source-only best selection, target monitoring labels, interruption, and resume. |
| 16 | `P17-A16-protected-regression` | P17-A9, P17-A15 | `protected-regression-agent` | `tests/phase_17/test_protected_methods_regression.py` only | Verify Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16 behavior contracts remain unchanged. |
| 17 | `P17-A17-cli-regression` | P17-A10, P17-A15 | `cli-regression-agent` | `tests/phase_17/test_cli_regression.py` only | Verify blocked real-run boundary, no publication evaluation, deterministic synthetic mode, and structured error output. |
| 18 | `P17-A18-architecture-candidate-decision` | P17-A4, P17-A15 | `architecture-decision-agent` | `specs/phase_17_ablations/equivalence_map.md` only | Record explicit approval or rejection of `mean_pool`. If no architectural candidate is approved, mark this action **NOT APPLICABLE — no architectural candidate approved** and do not add an aggregator implementation or test requirement beyond rejection coverage. |
| 19 | `P17-A19-integration-verification` | P17-A11 through P17-A18 | `verification-agent` | `tests/phase_17/test_integration_contract.py` only | Verify registry-to-CLI composition, all hashes, output directories, resume identity, target firewall, and blocked dispositions together. |

## Strict TDD sequence for each executable action

1. **RED:** the owning agent adds the smallest behavior-level test in its exclusive test file, runs the focused command, and records the observed failure.
2. **GREEN:** the owning agent implements the minimum behavior in its exclusive source file, then reruns the same focused command and records the pass.
3. **TRIANGULATE:** the owning agent covers at least one negative, alternate, or blocked case relevant to the action.
4. **REFACTOR:** only clarity-preserving changes are allowed while the focused tests remain green.

Documentation-only actions and the current specification action have no meaningful pre-implementation runtime behavior test; artifact validation is handled separately by the transaction controller.

## Validation commands

The implementation transaction must run focused tests first:

```text
python -m pytest -q tests/phase_17/test_registry_resolver.py
python -m pytest -q tests/phase_17/test_composition_diagnostics.py
python -m pytest -q tests/phase_17/test_target_firewall.py
python -m pytest -q tests/phase_17/test_output_identity.py
python -m pytest -q tests/phase_17/test_synthetic_lifecycle.py
python -m pytest -q tests/phase_17/test_protected_methods_regression.py
python -m pytest -q tests/phase_17/test_cli_regression.py
python -m pytest -q tests/phase_17/test_integration_contract.py
```

Then run the parent-authorized repository suite and static validation. No command in this task list authorizes real-data training, publication evaluation, package installation, or dependency mutation.

## Completion gates

Implementation is incomplete if any action lacks one owner, writes outside its ownership row, changes a protected method, creates a duplicate trainer, accepts a silent alias, selects a target checkpoint, runs a partial matrix, or lacks RED/GREEN/triangulation evidence. The transaction controller must also verify that no Phase 16 cleanup file or Phase 18 file changed.

## Closure status — authorized synthetic scope

P17-A1 through P17-A19 are complete for the authorized synthetic-only scope. No real-data run, publication evaluation, or Phase 18 work is authorized by this closure.

- **Focused evidence:** `python -m pytest -q -p no:cacheprovider tests/phase_17 --basetemp=artifacts/pytest-tmp-phase17-full-recheck` — **119 passed, 0 warnings**.
- **Lifecycle evidence:** 60 synthetic CLI plans (six candidates × five folds × two directions), approved validate-only coverage, one complete lifecycle pass, five target-firewall tests, 66 prior-method/Phase 15/16 targeted tests, and 43 registry/CLI tests passed.
- **Full-suite evidence:** `python -m pytest -q` — **exit 0, 1178 passed, 7 warnings, 1012.14s (0:16:52)**. The earlier 1059-pass result is pre-Phase 17 baseline evidence only.

Behavior covered by the integrated lifecycle/CLI tests is accepted as equivalent evidence for the planned standalone `test_output_identity.py` and `test_integration_contract.py` filenames. Those filenames are not fabricated; this equivalence does not claim that standalone files exist.
