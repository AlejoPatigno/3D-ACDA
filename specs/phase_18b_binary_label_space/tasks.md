# Phase 18B Binary Label Space Implementation Plan

**Status:** Planning; all production implementation tasks are pending or blocked. Before both gates pass, only documentation, specification refinement, and synthetic contract-test planning are permitted. That work is not implementation.

## Specification package

- [ ] Review `requirements.md` against the authoritative proposal.
- [ ] Review `design.md` for fixed class order, provenance, invariants, deterministic rejection, and fail-closed boundaries.
- [ ] Review `label_mapping.md` and `cohort_semantics.md` for ADNI/OASIS separation, duplicate/conflict exclusion, and pending OASIS policy.
- [ ] Review `migration_inventory.md`, `tensor_contracts.md`, `prediction_schema.md`, and `freeze_impact.md` for identity, loss, numeric, and compatibility completeness.
- [ ] Maintain the normative OpenSpec artifact at `openspec/changes/phase-18b-binary-label-space/specs/label-space/spec.md`.
- [ ] Record the Kimi/Gemini unavailability substitution: `fallback-review-1` and `fallback-review-2` are fresh, independent, non-authorizing, pending, and must use the same checklist.

## Synthetic contract-test planning only before gates

- [ ] Plan fixed vocabulary, canonical ADNI mapping, provenance, rejection, duplicate/conflict exclusion, and target-firewall contract tests.
- [ ] Plan binary tensor and checkpoint tests: `(B,2)` logits, `{0,1}` targets, `(B,K)` concepts, three-class rejection, and no partial load.
- [ ] Plan CDAN runtime-width tests for `(128,2)->256` and `(64,2)->128`, including backward gradients to `z` and `p` with no detach.
- [ ] Plan prototype/pseudo tests for raw logits shaped `(B,2)`, integer targets `{0,1}`, PyTorch-style `CrossEntropyLoss`, absent class 0, absent class 1, empty accepted set zero loss, and no target diagnosis; explicitly reject `BCEWithLogitsLoss`, sigmoid, and one-logit BCE.
- [ ] Plan prediction/evaluation tests for shared float64 `1e-6` and float32 `1e-5` tolerances, lower-index CN tie-break, null-plus-reason undefined metrics, and rejection of active `prob_mci`/`prob_ad`.
- [ ] Plan six identity-family collision tests for experiment, split, model/checkpoint, training metadata, evaluation result, and freeze against historical three-class identity.
- [ ] Plan split, sensitivity, authorization, and historical immutability tests without real manifests, hashes, counts, results, or freeze artifacts.

## Future production implementation batches (blocked; not started)

### Batch 1: Contract and provenance

- [ ] Implement fixed vocabulary and class-ID validation; dependency: both gates.
- [ ] Implement ADNI mapping with original-label and mapping provenance retention; dependency: both gates.
- [ ] Implement fail-closed invalid-label handling and duplicate/conflict exclusion; dependency: both gates and explicit policy.

### Batch 2: Model compatibility and losses

- [ ] Implement two-logit classifier and complete-checkpoint compatibility; dependency: Batch 1 and both gates.
- [ ] Preserve concept outputs `(B,K)`, CORAL/MMD, and target-label-free adaptation; dependency: reviewed invariants.
- [ ] Implement runtime CDAN width and gradient contract; dependency: reviewed tensor contract.
- [ ] Implement binary prototype/pseudo contracts; dependency: reviewed loss contract.

### Batch 3: Splits and identities

- [ ] Set and validate `REGENERATE_BINARY_SPLITS_REQUIRED`; dependency: approved cohort semantics.
- [ ] Implement binary-scoped split identity and proof-required reuse path; dependency: approved cohort semantics.
- [ ] Implement distinct identity families and historical three-class collision rejection; dependency: migration contract.

### Batch 4: Predictions and evaluation

- [ ] Emit and validate `prob_cn` and `prob_impaired`; reject active legacy fields; dependency: reviewed prediction schema.
- [ ] Validate shared probability tolerance, tie-break, 2x2 confusion orientation, and null-plus-reason metric policy; dependency: reviewed evaluation schema.
- [ ] Preserve source-validation macro-F1 as the sole best-checkpoint criterion; dependency: reviewed invariant.
- [ ] Add the specification-only CN-versus-AD sensitivity filter using original provenance; dependency: no execution.

### Batch 5: Interfaces and historical protection

- [ ] Add binary task/version fields to future artifact identities; dependency: six identity contracts.
- [ ] Add additive `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE` markers in new artifacts only; dependency: historical immutability.
- [ ] Document Phase 19 interface design only, without executing Phase 19; dependency: authorization flags.

## Required gates and substitution state

- [ ] Fresh fallback-review-1 specification review passes the complete checklist; substituted for unavailable Kimi; status: pending and non-authorizing.
- [ ] Fresh fallback-review-2 specification review passes the complete checklist; substituted for unavailable Gemini CLI; status: pending and non-authorizing.
- [ ] Maintainer approves canonical OASIS manifest and metadata-generation provenance; status: **BLOCKED**.
- [ ] Exact OASIS mapping, missing/out-of-domain, duplicate/conflict, and longitudinal policies are resolved; status: **BLOCKED**.
- [ ] Binary split reuse is proven valid or splits are regenerated; no real split is created by this package.
- [ ] Production implementation remains blocked until both OASIS semantics and both substituted reviews pass.

## Prohibited activities

- [ ] Do not call documentation or synthetic contract-test planning implementation.
- [ ] Do not run real ADNI/OASIS training or evaluation.
- [ ] Do not create real manifests, split hashes, class counts, results, or binary freeze artifacts.
- [ ] Do not execute Phase 19.
- [ ] Do not edit receipts, `.git/gentle-ai`, native lifecycle state, historical Phase 18 artifacts, or unrelated workspace changes.
- [ ] Do not claim tests, review, gate, lifecycle validation, publication authorization, or Phase 19 execution passed.

## Completion rule

A task becomes complete only when the relevant implementation or evidence is actually observed and independently recorded. This planning package intentionally marks no production implementation or test task complete.
