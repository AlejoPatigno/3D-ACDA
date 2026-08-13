# Phase 17 — Regression Audit

## Verdict

**PASS**

The fallback audit (requested Kimi audit; Kimi is unavailable in this Pi session) found no critical or scientific defect in the reviewed synthetic-only Phase 17 scope. This PASS is not approval for real execution, publication evaluation, or Phase 18.

## Audit basis

Audited directly:

- `AGENTS.md` and all Phase 17 SDD artifacts under `specs/phase_17_ablations/`;
- Phase 17 OpenSpec proposal, design, specification, tasks, and `state.yaml`;
- final Phase 17 registry/resolver/schema/output implementation, mean-pool model, CLI/configuration, lifecycle, documentation, and focused tests;
- protected-method regression coverage and Phase 15/16 boundary checks;
- relevant source/configuration paths for Phase 18 presence and generated-output boundaries.

## Approved candidate audit

| Candidate | One-component intervention | Audit result |
|---|---|---|
| `no_proto` | `lambda_proto = 0.0` | PASS; prototype term alone is disabled; pseudo-label, core, model, data, optimizer, epochs, splits, seeds, and artifacts are preserved. |
| `no_pl` | `lambda_pl = 0.0` | PASS; pseudo-label term alone is disabled; prototype and all preserved components remain canonical. |
| `no_cons` | `lambda_cons = 0.0` | PASS; full consistency term alone is disabled; warm is numerically unchanged because `warm_lambda_cons = 0.0`. |
| `no_concept` | `lambda_cbm = 0.0` | PASS; concept-supervision loss alone is disabled; the concept head and immutable concept artifacts remain present. |
| `no_anat` | `lambda_anat = 0.0` | PASS; anatomical term alone is disabled; concept targets, Jacobian artifacts, and all other terms remain preserved. |
| `mean_pool` | retained aggregator only: `z = U.mean(dim=1)`, `alpha = 1/K` | PASS; explicit `PADA-3DACB+MeanPoolAggregator` identity and distinct model hash; no contextual variant or runtime switch. |

The registry requires exact approved IDs and explicit synthetic-only approval. Unknown names, unsupported aliases, unresolved values, and unapproved candidates fail closed; no unsupported candidate is runnable.

## Required regression and scientific controls

- Warm/full objective contracts match the approved equations. Warm prototype and pseudo-label terms are not computed and are logged as zero.
- `no_domain_adaptation` remains `BLOCKED_NOT_PROVEN` as Source-Only. Zeroing two coefficients does not prove source-only loader, forward, gradient, method-identity, or output semantics.
- `no_ctx_encoder` remains equivalent to the current no-context PADA-3DACB behavior but invalid as an identity-patching technique. No duplicate runnable identity is created.
- `identity_ctx` remains helper-only. `full` remains invalid after the architecture revision. No `ContextualROIEncoder`, `ctx_enc`, Full/Lite switch, or patched Full construction is present in the Phase 17 production paths.
- Long aliases (`no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, `mean_pooling`, `source_only`) remain unsupported without explicit one-to-one approval. `lambda_proto = 0.2` remains unresolved and is not substituted for canonical `1.0`.
- Target adaptation is fail-closed to exactly `x`, `subject_id`, `subject_hash`, and `cohort`; forbidden labels, probabilities, concept/Jacobian targets, and other supervision/artifact fields are rejected before loss computation.
- Target adaptation/evaluation assignments remain disjoint with separate hashes. Target evaluation is labeled exactly `MONITORING ONLY — NOT A TRAINING LOSS` and cannot affect gradients, optimizer/scheduler state, checkpoint choice, hyperparameter choice, epoch count, resume choice, or candidate selection.
- Fixed warm/full epochs, source-validation macro-F1-only best-checkpoint selection, continuation after a best save, atomic artifacts, SHA-256 canonical identities, and identity-bound resume rejection are covered by the implementation and focused lifecycle evidence.
- Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16 boundaries remain regression-protected.

## Validation evidence

| Check | Evidence/status |
|---|---|
| Phase 17 focused suite | Parent-provided: **119 passed**. |
| Editable install | Parent-provided: passed. |
| Import/version | Parent-provided: passed; version `0.1.0`. |
| Ruff | Parent-provided: passed. |
| `git diff --check` | Parent-provided: passed. |
| Post-Phase 17 full suite | Directly executed `python -m pytest -q`: **exit 0, 1178 passed, 7 warnings, 1012.14s (0:16:52)**. The earlier **1059 passed** result is the **pre-Phase 17 baseline only**, not the current post-Phase 17 result. |

## Boundaries and limitations

- No real ADNI/OASIS training or evaluation was authorized or performed by this audit.
- No publication metrics, statistical comparison, leaderboard value, clinical conclusion, or real-data artifact is accepted as Phase 17 evidence. Phase 17 synthetic fixtures and lifecycle outputs are contract evidence only.
- No Phase 18 production files, configuration, tests, evaluation, plan, or artifact were found under the relevant `src/`, `configs/`, `tests/`, `docs/`, or `openspec/` paths.
- Existing unrelated pre-existing workspace/test artifacts are preserved and are not treated as Phase 17 scientific results.
- The documentation/task-equivalence note about integrated coverage versus separately named output-identity/integration test files is non-blocking and does not alter this PASS.

## Administrative boundary

Incident `#1793` remains preserved as an administrative delivery issue resolved by the approved Phase 16 receipt `review-79ee2a4308d2010c`. Its receipt provenance and native lifecycle validation gates remain mandatory. This audit does not stage files, create a review receipt, authorize a lifecycle transition, authorize real execution, authorize publication, or authorize Phase 18.

**Final verdict: PASS.**
