# Phase 17 — Dependency-Ordered Synthetic Implementation Tasks

## Execution rule

This task list is for the separately authorized synthetic implementation transaction. The current OpenSpec synchronization creates no production code, tests, configs, scripts, real-data run, publication result, or Phase 18 artifact. Exactly one agent owns each action. Agents MUST edit only the files named in their ownership row, MUST preserve Phase 16 cleanup and protected methods, and MUST stop for a scope update if a needed file is outside that row.

No task authorizes ADNI/OASIS loading, real training, publication evaluation, target-supervised adaptation, or Phase 18 work.

## Ordered task table

| Order | Action | Dependency | Exactly one agent | Exclusive file ownership | Required result |
|---:|---|---|---|---|---|
| 1 | `P17-A1-contract-fixture` | None | `contract-agent` | `tests/phase_17/fixtures/` only | Create deterministic in-memory registry, approval, matrix, and immutable-artifact fixtures. No MRI or real-data fixture. |
| 2 | `P17-A2-registry` | P17-A1 | `registry-agent` | `src/pada3dacb/ablations/registry.py` only | Define exact candidate records, provenance, dispositions, aliases, and protected-method references. Reject unknown and unapproved entries. |
| 3 | `P17-A3-resolver` | P17-A2 | `resolver-agent` | `src/pada3dacb/ablations/resolver.py` only | Resolve one approved candidate and one intervention; enforce canonical coefficients, architecture boundary, complete matrix, disjoint assignments, and structured blocked errors. |
| 4 | `P17-A4-equivalence` | P17-A2 | `equivalence-agent` | `src/pada3dacb/ablations/equivalence.py` only | Implement explicit `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, `full`, and alias dispositions. No silent alias or Source-Only substitution. |
| 5 | `P17-A5-composition` | P17-A3 | `composition-agent` | `src/pada3dacb/ablations/composition.py` only | Apply exactly one loss override or approved `mean_pool` aggregator replacement to current PADA-3DACB. No contextual patch or duplicate model. |
| 6 | `P17-A6-diagnostics` | P17-A5 | `diagnostics-agent` | `src/pada3dacb/ablations/diagnostics.py` only | Emit active/raw/weighted component diagnostics and prove inherited terms remain unchanged; warm adaptation remains absent and zero. |
| 7 | `P17-A7-output-schema` | P17-A3 | `output-agent` | `src/pada3dacb/ablations/output_schema.py` only | Validate checkpoint, history, prediction, equivalence-manifest, artifact-index, and required hash/loader fields. |
| 8 | `P17-A8-hash-identity` | P17-A3, P17-A7 | `identity-agent` | `src/pada3dacb/ablations/identity.py` only | Canonicalize JSON and compute all required SHA-256 identity hashes; reject mismatches and timestamp-dependent identity. |
| 9 | `P17-A9-trainer-adapter` | P17-A5, P17-A6, P17-A8 | `trainer-adapter-agent` | `src/pada3dacb/ablations/trainer_adapter.py` only | Adapt the existing trainer once; pass resolved contract, target firewall, diagnostics, fixed epochs, source-validation checkpoint selection, history, atomic outputs, and resume state. Do not implement a second trainer. |
| 10 | `P17-A10-cli` | P17-A4, P17-A7, P17-A8, P17-A9 | `cli-agent` | `src/pada3dacb/ablations/cli.py` only | Add preflight/resolve/synthetic-smoke/resume boundaries. Real data and publication evaluation remain authorization-gated. |
| 11 | `P17-A11-focused-registry-resolver-tests` | P17-A2, P17-A3, P17-A4 | `registry-test-agent` | `tests/phase_17/test_registry_resolver.py` only | Test exact IDs, approval requirement, alias rejection, `lambda_proto=0.2` versus `1.0`, one-intervention rule, architecture dispositions, and complete matrix validation. |
| 12 | `P17-A12-focused-composition-tests` | P17-A5, P17-A6 | `composition-test-agent` | `tests/phase_17/test_composition_diagnostics.py` only | Test each loss ablation changes exactly one full-stage weighted term; warm adaptation remains zero; `mean_pool` is uniform; no contextual field appears. |
| 13 | `P17-A13-firewall-tests` | P17-A9 | `firewall-test-agent` | `tests/phase_17/test_target_firewall.py` only | Test target adaptation accepts exactly `x`, `subject_id`, `subject_hash`, and `cohort`; rejects diagnosis/label/label_name/true_label/c_target/g_bar/diagnosis/stored probabilities/concept/Jacobian/artifact supervision fields; enforces disjoint monitoring assignments. |
| 14 | `P17-A14-output-hash-tests` | P17-A7, P17-A8 | `output-test-agent` | `tests/phase_17/test_output_identity.py` only | Test required schemas, stable hashes, changed model hash for pooling, unchanged model hash for loss-only ablations, atomic output validation, and hard-fail mismatch. |
| 15 | `P17-A15-synthetic-lifecycle` | P17-A9, P17-A10, P17-A13, P17-A14 | `lifecycle-agent` | `tests/phase_17/test_synthetic_lifecycle.py` only | Run a deterministic synthetic warm/full lifecycle with no real data; test checkpoint creation, source-only best selection, target monitoring labels, interruption, and exact resume. |
| 16 | `P17-A16-protected-regression` | P17-A9, P17-A15 | `protected-regression-agent` | `tests/phase_17/test_protected_methods_regression.py` only | Verify Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16 behavior contracts remain unchanged. |
| 17 | `P17-A17-cli-regression` | P17-A10, P17-A15 | `cli-regression-agent` | `tests/phase_17/test_cli_regression.py` only | Verify blocked real-run boundary, no publication evaluation, deterministic synthetic mode, and structured error output. |
| 18 | `P17-A18-architecture-candidate-decision` | P17-A4, P17-A15 | `architecture-decision-agent` | `specs/phase_17_ablations/equivalence_map.md` only | Record explicit approval or rejection of `mean_pool`. If no architectural candidate is approved, mark **NOT APPLICABLE — no architectural candidate approved** and add no aggregator implementation beyond rejection coverage. |
| 19 | `P17-A19-integration-verification` | P17-A11 through P17-A18 | `verification-agent` | `tests/phase_17/test_integration_contract.py` only | Verify registry-to-CLI composition, all hashes, output directories, resume identity, target firewall, and every blocked disposition together. |

## Strict TDD sequence for executable actions

Strict TDD is active for the implementation transaction. Every executable action MUST follow this sequence within its exclusive ownership boundary:

1. **RED:** add the smallest behavior-level test in the exclusive test file, run the focused command, and record the observed failure.
2. **GREEN:** implement the minimum behavior in the exclusive source file, rerun the same focused command, and record the observed pass.
3. **TRIANGULATE:** cover at least one negative, alternate, or blocked case relevant to the action, including target firewall, alias, unresolved coefficient, matrix, or resume cases where applicable.
4. **REFACTOR:** make clarity-preserving changes only while focused tests remain green.

The OpenSpec synchronization itself is documentation-only and has no meaningful pre-implementation runtime behavior test. Its validation exception is YAML/Markdown parsing plus `git diff --check`; it does not claim RED/GREEN implementation evidence.

## Required contract checks

The implementation transaction MUST preserve:

- exact approved IDs: `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`;
- exact interventions: `lambda_proto=0.0`, `lambda_pl=0.0`, `lambda_cons=0.0`, `lambda_cbm=0.0`, `lambda_anat=0.0`, and the exact uniform mean operation;
- canonical primary `lambda_proto=1.0` while retaining unresolved `lambda_proto=0.2` as blocked;
- one current PADA-3DACB architecture and one existing trainer;
- no target diagnosis labels in adaptation and monitoring-only target evaluation;
- complete direction/fold/seed matrices, fixed explicit epochs, and source-validation macro-F1-only checkpoint selection;
- atomic, hash-verified, resumable output identities;
- blocked `no_domain_adaptation`, `full`, `no_ctx_encoder`, `identity_ctx`, unsupported aliases, CFS, ACS, PCS, and QIS;
- no real data, publication metrics, publication conclusions, or Phase 18.

## Focused validation commands

Run focused tests first:

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

Then run only parent-authorized repository validation and static checks. No command in this task list authorizes package installation, dependency mutation, real-data training, publication evaluation, or lifecycle receipt changes.

## Completion gates

Implementation is incomplete if any action lacks one owner, writes outside its ownership row, changes a protected method, creates a duplicate trainer, accepts a silent alias, selects a target checkpoint, runs a partial matrix, lacks strict-TDD evidence, or violates the real-data/publication/Phase 18 boundary. The transaction controller MUST also verify that no Phase 16 cleanup file or unrelated path changed.

## Closure status — authorized synthetic scope

P17-A1 through P17-A19 are complete for the authorized synthetic-only scope. No real-data run, publication evaluation, or Phase 18 work is authorized by this closure.

- **Focused evidence:** `python -m pytest -q -p no:cacheprovider tests/phase_17 --basetemp=artifacts/pytest-tmp-phase17-full-recheck` — **119 passed, 0 warnings**.
- **Lifecycle evidence:** 60 synthetic CLI plans (six candidates × five folds × two directions), approved validate-only coverage, one complete lifecycle pass, five target-firewall tests, 66 prior-method/Phase 15/16 targeted tests, and 43 registry/CLI tests passed.
- **Full-suite evidence:** `python -m pytest -q` — **exit 0, 1178 passed, 7 warnings, 1012.14s (0:16:52)**. The earlier 1059-pass result is pre-Phase 17 baseline evidence only.

Behavior covered by the integrated lifecycle/CLI tests is accepted as equivalent evidence for the planned standalone `test_output_identity.py` and `test_integration_contract.py` filenames. Those filenames are not fabricated; this equivalence does not claim that standalone files exist.
