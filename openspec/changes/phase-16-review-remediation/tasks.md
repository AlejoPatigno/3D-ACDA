# Phase 16 Review Remediation — Implementation Tasks

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 760–900 total; Slice A ~220, Slice B ~260, Slice C ~280 |
| 400-line budget risk | High overall; Low per serial slice |
| Chained PRs recommended | Yes |
| Suggested split | Slice A → Slice B → Slice C; each slice includes its focused tests and evidence |
| Delivery strategy | auto-forecast; apply one bounded slice at a time and stop before 400 authored changed lines |
| Chain strategy | pending; resolve before creating or routing PRs |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

The forecast counts production code, tests, and active remediation evidence. No slice may continue after its forecast approaches 400 authored changed lines. Slice B depends on the completed, reviewable output of Slice A; Slice C depends on the completed, reviewable output of Slice B. Do not combine slices.

## Execution Guardrails

- This file is a plan only. No implementation, review lifecycle transition, commit, push, PR, release, publication, archive, or Phase 17 work is authorized by these tasks.
- Preserve native incident `#1793` and escalated receipt `review-a81b3edbc82c5830` exactly; do not edit, replace, restart, relabel, finalize, validate, or clear them during apply.
- The prior full-suite timeout remains incomplete evidence. Focused passes must never be reported as full-suite success.
- Real evaluation remains closed unless the implementation finds an already-approved local callback and satisfies the capability/provenance contract. Never invent a real-data loader, callback, dataset, or scientific value.
- No Kaggle, public/external dataset, network access, GPU path, notebook, real cohort run, or Phase 17 work.
- Use the existing project exception boundaries and fixture compatibility. Do not broaden metrics, preprocessing, model architecture, partitions, or scientific claims.

## Exclusive File Ownership and Serial Boundaries

All implementation and apply-owned verification actions are owned by the `implementation` role. The same role retains ownership of a file across RED/GREEN/TRIANGULATE/REFACTOR so no two work units edit it concurrently.

| Slice | Exclusive implementation-owned files | May start after | Must finish with |
|---|---|---|---|
| A | `src/pada3dacb/evaluation/concepts/schemas.py`, `src/pada3dacb/evaluation/concepts/provenance.py`, `src/pada3dacb/evaluation/concepts/discovery.py`, `tests/test_concept_provenance.py`, and `tests/test_concept_discovery.py` (including the focused schema/config cases; no broad schema suite) | Nothing; baseline only | Strict manifest/config/eligibility evidence and unchanged fixture behavior |
| B | `src/pada3dacb/evaluation/concepts/inference.py`, `scripts/evaluate_concepts.py`, `tests/test_concept_inference.py`, `tests/test_concept_modes.py`, and only the smallest required `tests/test_concept_cli.py` regression | Slice A focused evidence is reviewable | Authorization/load-order evidence and real path still closed without an approved local callback |
| C | `src/pada3dacb/evaluation/concepts/report.py`, `tests/test_concept_report.py`, `openspec/changes/phase-16-review-remediation/remediation-evidence.md` | Slice B focused evidence is reviewable | Non-destructive publication evidence and truthful remediation record |

`schemas.py` is one exclusive ownership track: Slice B may extend the capability contract only after Slice A's schema work is complete; it is not a parallel owner or a second edit stream.

## Slice A — Candidate Provenance and Configuration Eligibility

**Boundary:** only schemas, provenance, discovery, and their focused tests. Do not change inference, CLI execution, report publication, or review artifacts. Estimated authored change: ~220 lines.

### RED — establish failing focused tests

- [x] **A-RED-01** Add focused tests in `tests/test_concept_provenance.py` for the versioned manifest shape, lowercase SHA-256 validation, safe POSIX-relative paths, duplicate candidate keys, missing files, actual atlas/normalizer/checkpoint hash mismatch, and canonical ROI-order hashing; assert failure before eligibility and map each case to A-1, A-2, A-3, and A-5. **Start:** use isolated temporary fixture files and existing project test helpers only. **Finish:** tests fail for the current implementation for the intended missing/malformed/mismatched reasons. **Verification:** run `python -m pytest -q tests/test_concept_provenance.py`; if the configured runner is unavailable, record the exact failure without claiming a pass. **Rollback:** remove only the new focused tests; do not touch incident or receipt artifacts. <!-- sdd-owner: implementation -->
- [x] **A-RED-02** Add focused schema/config and discovery tests in `tests/test_concept_discovery.py` for missing/mistyped/out-of-range configuration, duplicate selectors, missing real manifest/atlas assignments, conflicting expected hashes, missing ROI labels, and fail-closed candidate exclusion with actionable issue strings; map to A-4 and A-5. **Start:** preserve non-strict fixture discovery cases as separate fixtures. **Finish:** new strict cases fail while existing fixture expectations remain the baseline. **Verification:** run `python -m pytest -q tests/test_concept_discovery.py`; do not use real data or checkpoints. **Rollback:** revert only this test addition. <!-- sdd-owner: implementation -->

### GREEN — implement the minimum strict boundary

- [x] **A-GREEN-01** Implement strict manifest/file-identity value objects and validation in `src/pada3dacb/evaluation/concepts/schemas.py`, preserving loose dataclass construction required by synthetic fixtures; validate schema version, required fields, lowercase hashes, integer ROI labels, selector uniqueness, safe relative paths, and configuration type/range/cross-field invariants without inventing scientific thresholds. Map to A-1 and A-4. **Start:** use the RED tests and existing schema/config conventions. **Finish:** valid canonical fixtures parse and invalid shapes fail closed with actionable errors. **Verification:** rerun `tests/test_concept_provenance.py` and `tests/test_concept_discovery.py` focused cases. **Rollback:** revert only Slice A schema changes; keep prior fixture APIs and valid output trees intact. <!-- sdd-owner: implementation -->
- [x] **A-GREEN-02** Implement canonical manifest parsing, actual atlas/normalizer/checkpoint identity checks, ROI-label/order agreement, and immutable verified-input values in `src/pada3dacb/evaluation/concepts/provenance.py`; hash files before parsing, reject missing/conflicting labels, and retain existing `compute_sha256_*` and `compute_artifact_hashes` behavior for materialized artifacts. Map to A-1, A-2, A-3, and A-5. **Start:** consume only the strict schema contract from A-GREEN-01. **Finish:** a valid manifest yields verified identities; every missing, mismatched, unsafe, or unassigned artifact blocks eligibility. **Verification:** focused provenance tests include a spy proving file hash precedes checkpoint inspection and no unsafe fallback exists. **Rollback:** revert only provenance changes; leave all prior result trees and receipt state untouched. <!-- sdd-owner: implementation -->
- [x] **A-GREEN-03** Update strict discovery validation in `src/pada3dacb/evaluation/concepts/discovery.py` to require exact manifest assignment, remove `weights_only=False` checkpoint inspection, return actionable issue-list exclusions for discovery/reporting, and make the real eligibility path blocking; preserve non-strict synthetic/fixture behavior. Map to A-1 through A-5. **Start:** integrate only the Slice A schemas/provenance contracts. **Finish:** no unverified candidate can reach model loading and no unrelated scientific policy changes are introduced. **Verification:** run the two Slice A focused test files and inspect changed paths. **Rollback:** revert only discovery changes and keep real evaluation closed. <!-- sdd-owner: implementation -->

### TRIANGULATE — verify cross-file invariants and regressions

- [x] **A-TRI-01** Add cross-boundary tests spanning `schemas.py`, `provenance.py`, and `discovery.py` that prove all requested candidates have exactly one manifest assignment, atlas/normalizer/checkpoint/candidate/runtime ROI identities agree, a missing or reordered label blocks, and any provenance/config issue occurs before model loading; map to A-2, A-3, and A-5. **Start:** use only local temporary fixtures and monkeypatched side-effect sentinels. **Finish:** all failure paths are fail-closed and valid fixture discovery remains compatible. **Verification:** run `python -m pytest -q tests/test_concept_provenance.py tests/test_concept_discovery.py`. **Rollback:** remove only these cross-boundary tests if Slice A is reverted. <!-- sdd-owner: implementation -->
- [x] **A-TRI-02** Run Slice A static checks on the owned paths: `python -m ruff check src/pada3dacb/evaluation/concepts/schemas.py src/pada3dacb/evaluation/concepts/provenance.py src/pada3dacb/evaluation/concepts/discovery.py tests/test_concept_provenance.py tests/test_concept_discovery.py`, `python -m py_compile` for the three production files, and `git diff --check`; record unavailable-tool failures literally. **Start:** after A-TRI-01. **Finish:** focused evidence is attributable only to Slice A. **Verification:** no full-suite pass is inferred from focused or static checks. **Rollback:** revert only Slice A files if the bounded slice cannot meet its contract. <!-- sdd-owner: implementation -->

### REFACTOR — preserve behavior and freeze the Slice A handoff

- [x] **A-REFACTOR-01** Refactor only within the Slice A ownership set to centralize duplicate validation and keep error messages actionable, without changing accepted valid inputs, fixture semantics, or scientific values; map to A-1 through A-5. **Start:** after RED/GREEN/TRIANGULATE pass. **Finish:** no dead duplicate validator or fail-open branch remains. **Verification:** rerun Slice A focused tests and static checks; compare the changed-file list to the ownership table. **Rollback:** revert the refactor only, preserving the last verified Slice A behavior. <!-- sdd-owner: implementation -->
- [x] **A-REFACTOR-02** Write the Slice A handoff evidence in the apply-progress record or designated phase evidence channel, listing exact focused commands/results, known limitations, and the next-slice dependency; explicitly state that incident `#1793`, receipt `review-a81b3edbc82c5830`, and the full-suite timeout are unchanged/incomplete. **Start:** only after A-REFACTOR-01. **Finish:** Slice A is reviewable and no Slice B file is changed. **Verification:** parent can inspect the evidence and changed-path boundary. **Rollback:** remove only newly created Slice A evidence; never edit native incident or receipt records. <!-- sdd-owner: implementation -->

- [x] **A-CORRECT-01** Close the handoff validator findings for strict atlas identity/labels and runtime ROI identity: require actual atlas-manager labels/hash and non-optional ordered runtime labels only in strict discovery, while preserving loose fixture behavior. **Verification:** focused negative tests cover missing and reordered atlas/runtime labels. <!-- sdd-owner: implementation -->
- [x] **A-CORRECT-02** Enforce exact strict manifest assignment for each candidate concept-artifact root and validate the minimum authorized configuration contract, including gate evidence, real paths, manifest assignment, and input/output-root non-overlap. **Verification:** focused negative tests cover root divergence, invalid gate/path types, missing paths, and overlap. <!-- sdd-owner: implementation -->
- [x] **A-CORRECT-03** Reject every backslash in POSIX-relative manifest paths and reconcile Slice A focused evidence with duplicate-key, direct atlas/normalizer/checkpoint file-hash mismatch, missing-file, label-order, assignment, and strict-config regression coverage. **Verification:** run focused tests and owned static checks; each direct file-hash mismatch test uses valid ROI-order metadata and proves checkpoint inspection is not reached; do not claim full-suite success. <!-- sdd-owner: implementation -->

## Slice B — Capability, Safe Loading, and CLI Seam

**Boundary:** only authorization, provenance-first safe checkpoint/model execution, the authoritative CLI seam, and focused mode/inference/CLI tests. Do not add a real-data loader. Estimated authored change: ~260 lines.

### RED — prove bypass and unsafe-order failures

- [x] **B-RED-01** Add tests in `tests/test_concept_inference.py` and `tests/test_concept_modes.py` proving missing/forged/stale capabilities fail before checkpoint load, model construction, forward, statistics, or writer calls; prove `torch.load(weights_only=False)` is never used and file identity precedes safe parsing; map to B-1, B-2, B-3, and B-5. **Start:** consume Slice A verified-input fixtures only. **Finish:** tests fail against the current direct-call and unsafe-load behavior. **Verification:** run the two focused test files with the project runner or record runner failure. **Rollback:** remove only new Slice B RED tests. <!-- sdd-owner: implementation -->
- [x] **B-RED-02** Add the smallest regression cases in `tests/test_concept_cli.py` for the authoritative `scripts/evaluate_concepts.py::_execute` path: unauthorized real requests remain blocked, capability creation requires canonical manifest/gate evidence, and no approved local callback means an actionable closed error rather than synthetic-as-real behavior; map to B-1 and B-4. **Start:** inspect the existing CLI path before editing. **Finish:** tests fail only where the seam is missing and do not require network, GPU, external data, or a new loader. **Verification:** run only this focused CLI test. **Rollback:** revert only the regression test. <!-- sdd-owner: implementation -->

### GREEN — implement the explicit capability and safe seam

- [x] **B-GREEN-01** Extend the exclusive `schemas.py` ownership track with the opaque process-local `RealEvaluationCapability` and `issue_real_evaluation_capability` contract: private issuer token, schema version, manifest digest, authorization digest, issuer label, lowercase evidence hashes, and keyword-only use; reject booleans, strings, forged visible-field objects, stale digests, and incomplete evidence. Map to B-1 and B-5. **Start:** only after Slice A handoff evidence is reviewable. **Finish:** capability issuance has no checkpoint/model/output side effects and cannot authorize by direct invocation alone. **Verification:** rerun capability RED tests and existing schema/fixture tests. **Rollback:** revert only the capability extension while preserving Slice A strict validation. <!-- sdd-owner: implementation -->
- [x] **B-GREEN-02** Implement provenance-first safe checkpoint identity and tensor-only inspection/loading in `src/pada3dacb/evaluation/concepts/inference.py`: hash/open identity first, use `weights_only=True`, require the supported mapping/state-dict/primitive metadata shape, reject unsupported formats, and never fall back to arbitrary object reconstruction. Map to B-2 and B-3. **Start:** receive only `VerifiedEvaluationInputs` from Slice A. **Finish:** every requested checkpoint is verified before model construction and unsupported formats fail closed. **Verification:** load-order spies assert `authorize < artifact_hash < checkpoint_hash < safe_load`; run focused inference tests. **Rollback:** revert only Slice B inference changes; do not restore `weights_only=False`. <!-- sdd-owner: implementation -->
- [x] **B-GREEN-03** Add the small real orchestration preflight in `src/pada3dacb/evaluation/concepts/inference.py` and route the authoritative `_execute` path in `scripts/evaluate_concepts.py` through it; require capability plus verified inputs before model construction, inference, statistics, or publication, while leaving synthetic and validate-only fixture paths explicit and deterministic. If no approved local callback exists, return a configuration error and keep real mode closed. Map to B-1, B-3, and B-4. **Start:** do not invent a loader or callback. **Finish:** direct real calls cannot bypass the gate and the CLI handoff introduces no new real data source. **Verification:** run inference/mode/CLI focused tests with event-order sentinels. **Rollback:** revert only the seam changes and leave real evaluation disabled. <!-- sdd-owner: implementation -->

### TRIANGULATE — verify execution ordering and compatibility

- [x] **B-TRI-01** Add one event-order test across authorization, artifact hashing, checkpoint hashing, safe load, model construction, forward, statistics, and publication; add tests for all-candidate preflight before first model construction, unsupported safe-load format without unsafe retry, direct inference/statistics rejection, and explicit fixture-only synthetic determinism. Map to B-1 through B-5. **Start:** use monkeypatched local callbacks only. **Finish:** no side effect occurs before the required predecessor event. **Verification:** run `tests/test_concept_inference.py tests/test_concept_modes.py tests/test_concept_cli.py` focused selections. **Rollback:** remove only the added triangulation tests. <!-- sdd-owner: implementation -->
- [x] **B-TRI-02** Run Slice B static checks: `python -m ruff check src/pada3dacb/evaluation/concepts/inference.py scripts/evaluate_concepts.py tests/test_concept_inference.py tests/test_concept_modes.py tests/test_concept_cli.py`, `python -m py_compile src/pada3dacb/evaluation/concepts/inference.py scripts/evaluate_concepts.py`, and `git diff --check`; preserve the full-suite timeout as incomplete. **Start:** after B-TRI-01. **Finish:** evidence names focused commands only. **Verification:** inspect that no external dataset, network, GPU, notebook, or Phase 17 path was added. **Rollback:** revert only Slice B if the budget or contract is exceeded. <!-- sdd-owner: implementation -->

### REFACTOR — keep the execution boundary narrow

- [x] **B-REFACTOR-01** Refactor only the Slice B ownership set to keep one authoritative real preflight, clear unauthorized/configuration errors, and explicit fixture-only lower-level helpers; do not add capability parameters to pure materialized statistics helpers or loosen legacy safe loading. Map to B-1 through B-5. **Start:** after Slice B triangulation. **Finish:** no duplicate real gate or hidden bypass remains. **Verification:** rerun all Slice B focused tests and static checks. **Rollback:** revert only the refactor; never reinstate unsafe loading. <!-- sdd-owner: implementation -->
- [x] **B-REFACTOR-02** Record Slice B handoff evidence with exact focused results, the absence/presence of an approved local callback, the unchanged closed default gate, and the unchanged escalated incident/receipt plus incomplete full-suite timeout. **Start:** after B-REFACTOR-01. **Finish:** Slice C can consume only the returned published-path contract and no report file is changed. **Verification:** parent reviews the Slice B file boundary and evidence. **Rollback:** remove only new Slice B evidence. <!-- sdd-owner: implementation -->

## Slice C — Report Versioning and Evidence

**Boundary:** only `report.py`, its focused tests, and the new remediation evidence file. Do not edit native incident/review artifacts or prior Phase 16 evidence. Estimated authored change: ~280 lines.

### RED — expose destructive and incomplete publication behavior

- [x] **C-RED-01** Add failing tests in `tests/test_concept_report.py` for byte-for-byte preservation under `overwrite=False`, deterministic `output.v000001` allocation, same-identity reuse, occupied/invalid sibling handling, no temporary leakage, and controlled concurrent reservations; map to C-1. **Start:** use local temporary directories and deterministic evaluation identities. **Finish:** current overwrite behavior fails the new preservation cases. **Verification:** run only the report focused tests. **Rollback:** remove only these tests. <!-- sdd-owner: implementation -->
- [x] **C-RED-02** Add failing report tests for unknown-tree rejection, atomic overwrite, restoration after injected stage/replace failure, manifest-last ordering, and manifest/artifact-index tampering; map to C-2. **Start:** reuse existing allowlist and rollback fixtures. **Finish:** tests detect any partial visibility or destructive cleanup. **Verification:** run `python -m pytest -q tests/test_concept_report.py`; no real evaluation is needed. **Rollback:** revert only the test additions. <!-- sdd-owner: implementation -->

### GREEN — implement non-destructive deterministic publication

- [x] **C-GREEN-01** Update `src/pada3dacb/evaluation/concepts/report.py` so `overwrite=False` preserves absent-path ergonomics, reuses a valid completed tree with identical `evaluation_identity`, rejects invalid/unknown existing trees without modifying them, and allocates the first free deterministic `output.vNNNNNN` destination for a different identity. Map to C-1. **Start:** consume Slice B's published-path contract; do not alter inference or statistics. **Finish:** the returned `Path` is the consumer-visible result and existing bytes remain unchanged. **Verification:** pass C-RED-01 focused tests. **Rollback:** revert only the non-overwrite branch; preserve prior valid trees. <!-- sdd-owner: implementation -->
- [x] **C-GREEN-02** Add the bounded cross-platform reservation lock, tokenized reservation/stage cleanup, atomic destination publication, completion-manifest-last ordering, generic completed-tree verification, and retained overwrite backup/restore behavior in `src/pada3dacb/evaluation/concepts/report.py`. Map to C-1 and C-2. **Start:** retain the existing allowlist and injected replacement seams. **Finish:** success/failure leaves no controlled temporary state and never deletes arbitrary user directories. **Verification:** pass C-RED-02 and concurrency/failure cases. **Rollback:** revert only Slice C report changes and keep the prior allowlisted tree intact. <!-- sdd-owner: implementation -->

### TRIANGULATE — verify publication and evidence boundaries

- [x] **C-TRI-01** Add integration-style report tests for repeated identical runs, different identities, occupied/invalid versions, controlled concurrent allocation, injected writer/replace failures, manifest-last write order, and byte-level prior-tree comparison; map to C-1 and C-2. **Start:** use deterministic local fixtures and no network/GPU/external data. **Finish:** no collision, partial destination, version skip attributable to the allocator, or leaked controlled stage/reservation remains. **Verification:** run `python -m pytest -q tests/test_concept_report.py`. **Rollback:** remove only the triangulation tests. <!-- sdd-owner: implementation -->
- [x] **C-TRI-02** Create `openspec/changes/phase-16-review-remediation/remediation-evidence.md` containing only actual focused command results, remediation-path lint/compile/diff checks, the prior full-suite timeout explicitly labeled incomplete, the unchanged escalated incident/receipt statement, and the no-real-cohort/no-network/no-GPU/no-notebook/no-Phase-17/no-lifecycle statement; map to C-3. **Start:** use results available after implementation; never invent counts or scientific values. **Finish:** wording does not claim full-suite success, approval, clearance, or completion of Phase 16. **Verification:** manually compare every claim with command output and confirm native incident/review files were not edited. **Rollback:** delete only this newly created evidence file; do not edit prior evidence or native receipt artifacts. <!-- sdd-owner: implementation -->

### REFACTOR — freeze truthful publication evidence

- [x] **C-REFACTOR-01** Refactor only `report.py` and `tests/test_concept_report.py` for naming, helper boundaries, and deterministic cleanup while preserving allowlist, atomicity, rollback, manifest-last, and non-overwrite contracts; map to C-1 and C-2. **Start:** after C-TRI-01. **Finish:** no test depends on timing, wall-clock identity, or arbitrary deletion. **Verification:** rerun report focused tests, ruff, `py_compile`, and `git diff --check`. **Rollback:** revert only the refactor and keep prior output trees untouched. <!-- sdd-owner: implementation -->
- [x] **C-REFACTOR-02** Finalize `remediation-evidence.md` with focused results only and verify its changed-path ownership; explicitly leave the full-suite timeout incomplete and incident `#1793`/receipt `review-a81b3edbc82c5830` escalated and unchanged. **Start:** after C-REFACTOR-01. **Finish:** Slice C is independently reviewable and below the 400-line budget. **Verification:** compare evidence claims to captured command output; do not run or report a full-suite pass. **Rollback:** remove only the new remediation evidence if Slice C is reverted. <!-- sdd-owner: implementation -->

## Acceptance Mapping and Slice Gates

| Requirement IDs | Required implementation evidence | Slice gate |
|---|---|---|
| A-1–A-5 | Strict manifest/config tests; actual file hashes; ROI-order agreement; actionable fail-closed exclusion; no model-load sentinel on failure | Slice A focused tests and static checks pass or are truthfully recorded as unavailable; changed lines remain <400 |
| B-1–B-5 | Opaque capability tests; unauthorized CLI/direct-call tests; file-hash-before-safe-load event order; `weights_only=True`; fixture-only deterministic modes; no approved callback means closed seam | Slice B focused tests and static checks pass or are truthfully recorded as unavailable; changed lines remain <400 |
| C-1–C-2 | Byte-preserving non-overwrite tests; deterministic version allocation/reuse; reservation/atomicity; allowlist/rollback/manifest-last tests | Slice C focused tests and static checks pass or are truthfully recorded as unavailable; changed lines remain <400 |
| C-3 | `remediation-evidence.md` with literal focused results, incomplete full-suite timeout, and immutable incident/receipt statement | Evidence claims match actual outputs and no lifecycle artifact changed |

## Rollback and Evidence Rules

- A failed slice rolls back only its owned production files, focused tests, and newly created remediation evidence. Never revert a prior successful slice as a shortcut.
- Rollback must preserve existing valid output trees byte-for-byte and must not restore `weights_only=False`, real execution, external data access, or any bypass.
- The escalated receipt and incident are administrative/native state, not slice outputs. They remain untouched regardless of implementation or test outcome.
- The full-suite timeout is incomplete evidence throughout. A focused test pass, lint pass, compile pass, or diff check cannot upgrade it.
- If a focused test runner is unavailable, times out, or fails for an unrelated pre-existing reason, record the exact command and status; do not substitute a scientific value or claim success.

## Final Parent / Lifecycle Checklist

These are parent-owned post-apply bounded-review and lifecycle-gate actions only; they are not implementation work.

- [ ] Confirm Slice A, B, and C were applied serially, each stayed below 400 authored changed lines, and each has a readable focused evidence record before allowing the next slice. <!-- sdd-owner: parent -->
- [ ] Confirm the final changed-path manifest contains only the ownership-table paths plus the new remediation evidence, with no incident, receipt, Phase 17, notebook, dataset, network, or GPU changes. <!-- sdd-owner: parent -->
- [ ] Confirm native incident `#1793` and escalated receipt `review-a81b3edbc82c5830` remain byte-for-byte/state-for-state unchanged and escalated. <!-- sdd-owner: parent -->
- [ ] Confirm the prior full-suite timeout remains explicitly incomplete and no artifact claims full-suite success, Phase 16 approval, review clearance, or scientific validity. <!-- sdd-owner: parent -->
- [ ] Run only the applicable bounded post-apply review/lifecycle validation required by the parent workflow; do not start a new review transaction or alter the escalated receipt from this task plan. <!-- sdd-owner: parent -->
- [ ] Keep Phase 17 blocked until a separate explicit approval and lifecycle decision; do not create or continue Phase 17 artifacts from this change. <!-- sdd-owner: parent -->
