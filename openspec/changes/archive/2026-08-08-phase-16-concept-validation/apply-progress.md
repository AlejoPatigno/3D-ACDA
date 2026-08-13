# Apply Progress — phase-16-concept-validation

## Current apply invocation — WU-01 (blocked by workload decision)

**blocked** — implementation did not start. The authoritative task forecast requires a resolved delivery path before applying a high-risk, chained workload.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec is authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`
- `allowedEditRoots`: [`C:\\Users\\LOQ\\Desktop\\PADA-3DACB`]
- `taskProgress`: 0 of 65 complete; 65 pending

### Workload gate

The task forecast contains:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: feature-branch-chain`
- `400-line budget risk: High`

The parent action context did not resolve `auto-chain`, a selected chain mode (`stacked-to-main` or `feature-branch-chain`), or an explicit `exception-ok`/`size:exception` approval. Per the apply contract, no production edits or task checkbox updates are authorized until that delivery path is supplied. The requested WU-01 scope is otherwise identified and remains unchecked.

### Files changed

- `openspec/changes/phase-16-concept-validation/apply-progress.md` — recorded this blocked invocation only.

### Tests

Not run; implementation was not authorized to start.

### Remaining tasks

All WU-01 implementation tasks remain unchecked in the persisted tasks artifact:

- [ ] Extract and reconcile tensor contracts, aggregation rules, metric equations, provenance gates, output names, and manuscript-score dispositions across the Phase 16 specification files. <!-- sdd-owner: implementation -->
- [ ] Record unresolved CFS/ACS/PCS/QIS definitions as `BLOCKED` and document the transparent metric fallback without inventing equations. <!-- sdd-owner: implementation -->
- [ ] Verify ownership, dependency order, prohibited paths, and the under-400-line slice boundary in `specs/phase_16_concept_validation/agent_plan.yaml`. <!-- sdd-owner: implementation -->
- [ ] Verify the specification set is internally consistent and all referenced paths exist before implementation begins. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-01

**blocked** — implementation did not start because the required review-workload delivery path is unresolved in the parent action context.

The request selects WU-01 but does not provide `auto-chain`, a selected chain mode (`stacked-to-main` or `feature-branch-chain`), or an explicit `exception-ok`/`size:exception` approval. Because the task forecast marks chained PRs as recommended and 400-line budget risk as High, no repository implementation or task checkbox edits are authorized.

No tests ran. No implementation-owned task was completed.

## Current apply attempt — WU-01

**blocked** — implementation did not start because the review-workload delivery path is unresolved.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec is authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`
- `allowedEditRoots`: [`C:\\Users\\LOQ\\Desktop\\PADA-3DACB`]
- `taskProgress`: 0 of 65 complete; 65 pending

### Workload gate

The authoritative task forecast requires a resolved delivery path before apply:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: feature-branch-chain`
- `400-line budget risk: High`

The apply request names WU-01 but does not resolve `auto-chain`, a selected chained mode (`stacked-to-main` or `feature-branch-chain`), or an explicitly accepted `size:exception`. No production or test files were edited.

### WU-01 remaining implementation tasks

- [ ] Extract and reconcile tensor contracts, aggregation rules, metric equations, provenance gates, output names, and manuscript-score dispositions across the Phase 16 specification files. <!-- sdd-owner: implementation -->
- [ ] Record unresolved CFS/ACS/PCS/QIS definitions as `BLOCKED` and document the transparent metric fallback without inventing equations. <!-- sdd-owner: implementation -->
- [ ] Verify ownership, dependency order, prohibited paths, and the under-400-line slice boundary in `specs/phase_16_concept_validation/agent_plan.yaml`. <!-- sdd-owner: implementation -->
- [ ] Verify the specification set is internally consistent and all referenced paths exist before implementation begins. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Historical blocked attempt

**blocked** — implementation did not start.

## Structured status consumed

- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session, with OpenSpec authoritative because `openspec/` exists)
- `applyState`: `blocked`
- `nextRecommended`: `resolve-blockers`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`
- `allowedEditRoots`: [`C:\\Users\\LOQ\\Desktop\\PADA-3DACB`]
- historical blocker: an earlier status read reported `tasks.md has no markdown task checkboxes`; the current authoritative status now reports 65 valid task rows.

## Workload gate

The task plan reports:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: feature-branch-chain`
- `400-line budget risk: High`

No resolved delivery path or chain strategy was supplied in the apply request. Apply therefore remains blocked by the workload gate as well as the authoritative task-artifact blocker.

## Completed tasks

None. No implementation-owned task was selected or modified.

## Files changed

- `openspec/changes/phase-16-concept-validation/apply-progress.md` — recorded this blocked attempt only.

## Tests

Not run; implementation was not authorized to start.

## Remaining action

Repair the authoritative `openspec/changes/phase-16-concept-validation/tasks.md` so implementation tasks are represented by markdown checkbox rows with valid ownership markers, then provide a resolved delivery path/chain strategy for the high-risk chained workload. Re-run structured SDD status before applying.

## Task checkbox reconciliation

The persisted tasks artifact was re-read. It contains 65 valid markdown task checkboxes, all unchecked; no completed task can be truthfully marked `- [x]` and no task was reported complete.

## Deviations and risks

- No production or test code was edited.
- No review, validation, receipt, or delivery gate was started.
- Existing `verify-report.md` claims completion, but the authoritative native status reports the tasks artifact as structurally invalid; the native status was obeyed.

## Current apply attempt — WU-01 (workload decision still required)

**blocked** — implementation did not start. The authoritative task forecast marks this workload as chained and high-risk, but the parent action context did not resolve a delivery path.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:\Users\LOQ\Desktop\PADA-3DACB`
- `allowedEditRoots`: [`C:\Users\LOQ\Desktop\PADA-3DACB`]
- `taskProgress`: 0 of 65 complete; 65 pending

### Workload gate

The persisted `Review Workload Forecast` says:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: feature-branch-chain`
- `400-line budget risk: High`

WU-01 was requested, but the parent prompt did not provide `auto-chain`, a selected chain mode (`stacked-to-main` or `feature-branch-chain`), or explicit `exception-ok`/`size:exception` approval. Per the apply workload contract, no implementation edits or task checkbox updates are authorized until that delivery path is resolved.

### WU-01 remaining implementation tasks

- [ ] Extract and reconcile tensor contracts, aggregation rules, metric equations, provenance gates, output names, and manuscript-score dispositions across the Phase 16 specification files. <!-- sdd-owner: implementation -->
- [ ] Record unresolved CFS/ACS/PCS/QIS definitions as `BLOCKED` and document the transparent metric fallback without inventing equations. <!-- sdd-owner: implementation -->
- [ ] Verify ownership, dependency order, prohibited paths, and the under-400-line slice boundary in `specs/phase_16_concept_validation/agent_plan.yaml`. <!-- sdd-owner: implementation -->
- [ ] Verify the specification set is internally consistent and all referenced paths exist before implementation begins. <!-- sdd-owner: implementation -->

### Verification

- Tests not run; implementation was not authorized to start.
- No repository production/test files changed.
- No review, receipt, or delivery gate was started.
- Persisted `tasks.md` was re-read: all WU-01 implementation rows remain visibly unchecked (`- [ ]`).

### Skill resolution

No parent-injected `SKILL.md` path or installed phase-specific `sdd-apply` skill was available; the executor instructions and global strict-TDD guidance were used as degraded fallback. Reported as `none`.

## Current apply invocation — WU-01 (blocked: unresolved delivery path)

**Status:** blocked before implementation. The authoritative task forecast still reports `Chained PRs recommended: Yes`, `Chain strategy: feature-branch-chain`, and `400-line budget risk: High`. The parent request selects WU-01 but does not explicitly resolve `auto-chain`, `stacked-to-main`, `feature-branch-chain`, or `exception-ok`/`size:exception`.

No production files, tests, or persisted task checkboxes were changed. No tests, review actors, receipts, or delivery gates were started. WU-01 remains the next implementation slice with all four implementation-owned rows unchecked.

**Exact decision needed before apply:** provide `auto-chain` with a chain strategy (recommended `feature-branch-chain` or `stacked-to-main`), or explicitly approve `exception-ok`/`size:exception`. The existing native receipt #1793 remains a downstream delivery blocker only and does not itself block synthetic implementation once the workload path is resolved.

## Latest apply invocation — WU-01 (blocked by unresolved delivery path)

**Status:** blocked before implementation. The authoritative workload forecast requires a resolved delivery path before applying this high-risk, chained workload. The request selected WU-01 but did not provide `auto-chain`, a selected chain mode, or explicit `exception-ok`/`size:exception` approval.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`
- `allowedEditRoots`: [`C:\\Users\\LOQ\\Desktop\\PADA-3DACB`]
- `taskProgress`: 0 of 65 complete; 65 pending
- `actionContext.warnings`: none

### Workload gate

The persisted `Review Workload Forecast` says:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: pending`
- `400-line budget risk: High`

The exact decision needed before apply is a resolved delivery path: provide `auto-chain` with `stacked-to-main` or `feature-branch-chain`, or explicitly approve `exception-ok`/`size:exception`. No production files, tests, or persisted task checkboxes were changed. No tests, review actors, receipts, or delivery gates were started.

### WU-01 remaining implementation tasks

- [ ] Extract and reconcile tensor contracts, aggregation rules, metric equations, provenance gates, output names, and manuscript-score dispositions across the Phase 16 specification files. <!-- sdd-owner: implementation -->
- [ ] Record unresolved CFS/ACS/PCS/QIS definitions as `BLOCKED` and document the transparent metric fallback without inventing equations. <!-- sdd-owner: implementation -->
- [ ] Verify ownership, dependency order, prohibited paths, and the under-400-line slice boundary in `specs/phase_16_concept_validation/agent_plan.yaml`. <!-- sdd-owner: implementation -->
- [ ] Verify the specification set is internally consistent and all referenced paths exist before implementation begins. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

### Verification

- Persisted tasks were not modified; all WU-01 implementation rows remain visibly unchecked.
- `apply-progress.md` was cumulatively updated; prior blocked history was preserved.
- No code or tests were edited.

### Skill resolution

`fallback-path`: no parent-injected phase skill path was provided; global status and strict-TDD support guidance were loaded. Strict TDD is inactive per `openspec/config.yaml`.


## Current apply invocation — WU-01 completed

**status:** completed for the assigned WU-01 slice. The parent prompt resolved the workload path as `auto-chain` with `feature-branch-chain`; implementation remained limited to the specification work unit and did not create branches, commits, pull requests, review receipts, or delivery gates.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress`: 4 of 65 complete; 61 pending
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-01 / T-16-01, specification reconciliation only; WU-02 and later work are deferred.
- WU-01 forecast envelope after reconciliation: 370 additions-plus-deletions maximum across its listed paths; hard ceiling 400; no size exception.
- Native receipt #1793 remains a downstream administrative delivery blocker. No branch, tracker PR, child PR, commit, or delivery action was created.

### Completed tasks and persisted checkbox updates

The four WU-01 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion:

- Extract/reconcile tensor, aggregation, metric, provenance, output, and manuscript-score contracts.
- Record CFS/ACS/PCS/QIS as `BLOCKED` with transparent fallback metrics.
- Verify agent-plan ownership, dependency order, prohibited paths, and the under-400-line boundary.
- Verify specification-set consistency and referenced authoritative paths.

### Files changed

- `specs/phase_16_concept_validation/agent_plan.yaml` — fixed YAML ownership-list syntax, reconciled WU-01 forecast to a 400-line ceiling, and recorded 14 actions / 66 owned paths / zero duplicates.
- `specs/phase_16_concept_validation/tasks.md` — corrected the reference-test path to `tests/test_concept_statistics_edge_cases.py`.
- `specs/phase_16_concept_validation/decisions.md` — added D-16-21 executable-contract reconciliation and verification evidence.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the four WU-01 implementation rows complete; parent-owned rows preserved unchanged.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative progress record.

### Verification evidence

- `python` YAML parse and ownership validation: PASS (`actions=14`, `owned_paths=66`, `duplicates=0`).
- WU-01 forecast sum validation: PASS (`370 <= 400`).
- WU-01 specification and authoritative-input path existence check: PASS (12 required files).
- Contract marker check for CFS/ACS/PCS/QIS, BLOCKED disposition, not-applicable methods, and `authorized: false`: PASS.
- Task ownership-marker validation: PASS; no malformed markers.
- `git diff --check` on changed WU-01 files: PASS.
- Tests were not run: this work unit changes specification artifacts only, and `openspec/config.yaml` declares no test runner.

### Deviations from design

No production implementation paths, training/adaptation paths, tests, or Phase 17 paths were changed. The only corrections were specification integrity fixes required by WU-01: an invalid YAML sequence item, stale ownership-validation counts, an over-400 WU-01 forecast envelope, and one inconsistent future reference-test filename.

### Skill resolution

`fallback-path`: no parent-injected phase skill path was available. Loaded global `gentle-ai` and `gentle-ai-chained-pr` skill files. Strict TDD is inactive per `openspec/config.yaml`; no RED/GREEN cycle was required.

### Remaining implementation-owned tasks (exact unchecked persisted lines)
- [ ] Review the Phase 16 contract for invented score definitions, target-label leakage, incorrect subject aggregation, causal overclaiming, and missing unavailable-state handling. <!-- sdd-owner: implementation -->
- [ ] Record PASS or blocking findings with evidence and explicitly confirm that real evaluation remains gated. <!-- sdd-owner: implementation -->
- [ ] Do not start implementation work while `specs/phase_16_concept_validation/spec_review.md` contains an unresolved blocker. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for schema validation, canonical class/ROI contracts, candidate discovery, read-only dataset construction, provenance mismatch exclusion, and no-grad tensor extraction using deterministic CPU fixtures. <!-- sdd-owner: implementation -->
- [ ] Implement typed concept-evaluation records and validation for tensor shapes, finiteness, normalized concept ranges, alpha normalization, class order, and canonical ROI order. <!-- sdd-owner: implementation -->
- [ ] Implement configured-root checkpoint/artifact discovery for eligible PADA methods and explicit not-applicable statuses for AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [ ] Implement read-only source-validation and target-evaluation dataset construction plus exact provenance/hash validation; reject missing or conflicting candidates without crashing the pipeline. <!-- sdd-owner: implementation -->
- [ ] Implement CPU-default checkpoint loading and no-grad forward extraction for all required tensors without training imports, optimizer state, parameter updates, or normalizer/Jacobian recomputation. <!-- sdd-owner: implementation -->
- [ ] Triangulate with invalid-shape, invalid-hash, non-finite, alpha-sum, target-partition, and gradient/parameter-immutability tests; then refactor only after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_schemas.py tests/test_concept_dataset.py tests/test_concept_discovery.py tests/test_concept_provenance.py tests/test_concept_inference.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for source OOF uniqueness, target fold ensembles, fold-then-seed aggregation, per-seed retention, direction separation, and immutable `c_target`/`g_bar`. <!-- sdd-owner: implementation -->
- [ ] Implement subject-level aggregation so repeated fold/seed outputs never become independent subjects and transfer directions are never pooled. <!-- sdd-owner: implementation -->
- [ ] Implement global, per-subject, and per-ROI concept-fidelity MAE, RMSE, bias, Pearson, and Spearman metrics. <!-- sdd-owner: implementation -->
- [ ] Implement anatomical consistency against `g_bar`, keeping unweighted descriptive metrics separate from the canonical weighted anatomy score. <!-- sdd-owner: implementation -->
- [ ] Implement explicit correlation availability status and reasons `constant_roi`, `insufficient_samples`, and `numerical_error`; never substitute zero for unavailable correlations. <!-- sdd-owner: implementation -->
- [ ] Triangulate against direct numerical references, singleton/constant ROIs, insufficient samples, weighted-score cases, and non-finite inputs; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_aggregation.py tests/test_concept_fidelity.py tests/test_concept_anatomy.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for latent/concept predictive metrics, top-1 agreement/disagreement, JS divergence, consistency-loss direction, per-class disagreement counts, and separation from concept fidelity. <!-- sdd-owner: implementation -->
- [ ] Implement head-agreement metrics with fixed class order and explicit probability handling. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for fold/seed ROI profiles, pairwise Spearman correlation, mean pairwise correlation, per-ROI standard deviation, configured top-k Jaccard, and rank dispersion. <!-- sdd-owner: implementation -->
- [ ] Implement ROI stability using the terms `attention profile`, `concept profile`, and `ROI stability`; reject causal-importance, biomarker, disease-mechanism, and equivalent causal terminology in generated contracts. <!-- sdd-owner: implementation -->
- [ ] Implement descriptive CN/MCI/AD concept, `c_target`, and `g_bar` profiles with class support and subject-level bootstrap hooks; do not add unrestricted ROI-by-ROI inference. <!-- sdd-owner: implementation -->
- [ ] Triangulate with hand-computed JS/agreement values, one-instance stability behavior, top-k configuration validation, empty-class handling, and terminology assertions; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_agreement.py tests/test_concept_stability.py tests/test_concept_class_profiles.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests proving reuse of Phase 15 subject-level stratified bootstrap with explicit seed, replicate accounting, no ROI/fold-level resampling, and deterministic results. <!-- sdd-owner: implementation -->
- [ ] Implement paired subject comparisons for `prototype_pseudo` versus `source_only`, `coral`, `mmd`, and `cdan` across concept MAE, anatomy MAE, and JS divergence. <!-- sdd-owner: implementation -->
- [ ] Implement Holm correction separately by direction, checkpoint policy, and metric family with exactly four PADA comparator slots; exclude AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [ ] Generate all required machine-readable tables with ROI-indexed vectors and all required figures using fixed ROI order and predeclared top-k values, without favorable-ROI selection or intervention figures. <!-- sdd-owner: implementation -->
- [ ] Triangulate bootstrap invalid/unavailable replicate accounting, paired-subject alignment, Holm reference results, complete output names, and deterministic figure/table fixtures; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [ ] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [ ] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->
- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks (preserved; exact unchecked persisted lines)
- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Current apply invocation — WU-02 blocked by unresolved delivery path

**status:** blocked before implementation. The next implementation work unit is WU-02 / T-16-02 (independent scientific review), but the parent prompt did not provide the required delivery decision for the high-risk chained workload.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress`: 4 of 65 complete; 61 pending
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload gate

The persisted `Review Workload Forecast` reports:

- `Decision needed before apply: No`
- `Chained PRs recommended: Yes`
- `Chain strategy: pending`
- `400-line budget risk: High`

The exact decision needed before apply is `auto-chain` with a selected chain strategy (`stacked-to-main` or `feature-branch-chain`), or explicit `exception-ok` / `size:exception` approval. No production or test files were edited, no task checkbox was changed, and no tests or review/delivery actors were started.

### Remaining next-work-unit tasks

WU-02 remains fully unchecked in the persisted tasks artifact:

- [ ] Review the Phase 16 contract for invented score definitions, target-label leakage, incorrect subject aggregation, causal overclaiming, and missing unavailable-state handling. <!-- sdd-owner: implementation -->
- [ ] Record PASS or blocking findings with evidence and explicitly confirm that real evaluation remains gated. <!-- sdd-owner: implementation -->
- [ ] Do not start implementation work while `specs/phase_16_concept_validation/spec_review.md` contains an unresolved blocker. <!-- sdd-owner: implementation -->

### Files changed

- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this blocked invocation; no implementation files changed.

### Tests

Not run; implementation was not authorized to start.

### Deviations and risks

- WU-02 is a review/specification-only slice; no code, tests, or production paths were modified.
- Native receipt #1793 remains a downstream administrative delivery blocker and was not acted on.
- Parent-owned lifecycle rows remain deferred and byte-for-byte unchanged.

### Skill resolution

`fallback-path`: no parent-injected phase skill path was provided; global SDD status guidance was used. Strict TDD is inactive because `openspec/config.yaml` declares `strict_tdd: false` and no test runner.

## Current apply invocation — WU-02 completed

**status:** completed for the assigned WU-02 slice. The independent scientific specification review is `PASS`; no production implementation was started.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec is authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress` before this slice: 4 of 65 complete; 61 pending
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-02 / T-16-02, specification review only; WU-03 and later work are deferred.
- WU-02 target is `<=400` changed lines; actual review-file change remains within that boundary. No size exception was used.
- Native receipt #1793 remains a downstream administrative delivery blocker. No branch, commit, pull request, review actor, receipt, or delivery gate was created.

### Completed tasks and persisted checkbox updates

The three WU-02 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion.

- Reviewed invented score definitions, target-label isolation, subject aggregation, causal overclaiming, and unavailable handling.
- Recorded a `PASS` verdict with evidence and confirmed the real-run gate remains closed.
- Confirmed implementation must not begin while `spec_review.md` contains an unresolved blocker; no blocker remains.

### Files changed

- `specs/phase_16_concept_validation/spec_review.md` — replaced the stale review with the current evidence-backed PASS review.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the three WU-02 implementation rows complete.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative progress record.

### Verification evidence

- Review evidence check: PASS for manuscript-score blocking, target-label firewall, fold/seed subject aggregation, causal terminology restrictions, unavailable-state propagation, method applicability, provenance, and `authorized: false` real-run gating.
- Ownership-marker scan: PASS; no malformed task markers.
- `git diff --check`: PASS for the WU-02 review/task changes.
- Tests not run: WU-02 is a specification-only review slice and `openspec/config.yaml` declares no test runner.

### Deviations from design

No deviation from the approved design. The stale prior review contained unsupported downstream implementation/test claims and an inconsistent six-slot Holm statement; the new review limits evidence to the contract and records the required four-comparator family and implementation gate.

### Remaining implementation-owned tasks

The cumulative task list above preserves the exact unchecked implementation rows. The next dependency-ready rows are:

- [ ] Add RED tests for schema validation, canonical class/ROI contracts, candidate discovery, read-only dataset construction, provenance mismatch exclusion, and no-grad tensor extraction using deterministic CPU fixtures. <!-- sdd-owner: implementation -->
- [ ] Implement typed concept-evaluation records and validation for tensor shapes, finiteness, normalized concept ranges, alpha normalization, class order, and canonical ROI order. <!-- sdd-owner: implementation -->
- [ ] Implement configured-root checkpoint/artifact discovery for eligible PADA methods and explicit not-applicable statuses for AAGN/FasterSNN. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

### Skill resolution

`fallback-path`: no parent-injected phase skill path was available; global SDD status and strict-TDD guidance were used. Strict TDD is inactive because `openspec/config.yaml` declares `strict_tdd: false` and no test runner.

## Current apply invocation — WU-03 completed

**status:** completed for the assigned WU-03 / T-16-03 discovery-inference slice. Existing Phase 16 concept-evaluation implementation was verified and tightened with contract-focused validation; no training, adaptation, Phase 17, review, receipt, or delivery actions were started.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress` before this slice: 7 of 65 complete; 58 pending
- `taskProgress` after this slice: 14 of 65 complete; 51 pending
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-03 / T-16-03 only; WU-04 and later remain deferred to subsequent chain slices.
- No size exception was used. No branch, commit, pull request, review actor, receipt, or delivery gate was created.

### Completed tasks and persisted checkbox updates

The seven WU-03 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion: RED contract tests; typed schema validation; configured discovery and explicit AAGN/FasterSNN not-applicable status; read-only dataset/provenance handling; CPU/no-grad inference; triangulation; and focused verification.

### Files changed

- `src/pada3dacb/evaluation/concepts/schemas.py` — enforce normalized `[0, 1]` concept, concept-target, and anatomy-target ranges.
- `src/pada3dacb/evaluation/concepts/dataset.py` — enforce ROI tensor shapes/ranges, probability contracts, and prediction argmax consistency.
- `src/pada3dacb/evaluation/concepts/discovery.py` — make discovery deterministic and report AAGN/FasterSNN as not applicable before filesystem probing.
- `src/pada3dacb/evaluation/concepts/inference.py` — require experiment, model, and training hashes before loading.
- `tests/test_concept_schemas.py` — add normalized-range rejection tests.
- `tests/test_concept_dataset.py` — add probability-shape rejection coverage.
- `tests/test_concept_discovery.py` — add no-checkpoint not-applicable coverage.
- `tests/test_concept_inference.py` — add missing-training-hash coverage and normalize the synthetic model fixture.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the seven WU-03 implementation rows complete; parent-owned rows preserved.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- RED focused run before production edits: 6 expected failures covering normalized ranges, probability shape, not-applicable discovery, and training-hash requirements.
- GREEN focused verification: `python -m pytest tests/test_concept_schemas.py tests/test_concept_dataset.py tests/test_concept_discovery.py tests/test_concept_provenance.py tests/test_concept_inference.py -q --basetemp=artifacts/pytest-tmp-phase16` — **105 passed**, one Windows pytest cache-permission warning.
- Ruff focused check: PASS.
- `git diff --check` for WU-03 paths: PASS.
- Triangulation coverage includes invalid shapes, invalid provenance hashes, non-finite tensors, alpha sums, precomputed target presence/shape, no-grad inference, and checkpoint immutability-by-loading contract; no training or adaptation imports were added.

### Deviations from design

No scope deviation. The implementation tightened three implicit design contracts that were previously under-validated: normalized tensor ranges, standalone dataset tensor/probability shapes, and explicit not-applicable discovery independent of checkpoint presence. Checkpoint loading now also fails closed when the required training hash is absent.

### Remaining implementation-owned tasks (exact unchecked persisted lines)

- [ ] Add RED tests for source OOF uniqueness, target fold ensembles, fold-then-seed aggregation, per-seed retention, direction separation, and immutable `c_target`/`g_bar`. <!-- sdd-owner: implementation -->
- [ ] Implement subject-level aggregation so repeated fold/seed outputs never become independent subjects and transfer directions are never pooled. <!-- sdd-owner: implementation -->
- [ ] Implement global, per-subject, and per-ROI concept-fidelity MAE, RMSE, bias, Pearson, and Spearman metrics. <!-- sdd-owner: implementation -->
- [ ] Implement anatomical consistency against `g_bar`, keeping unweighted descriptive metrics separate from the canonical weighted anatomy score. <!-- sdd-owner: implementation -->
- [ ] Implement explicit correlation availability status and reasons `constant_roi`, `insufficient_samples`, and `numerical_error`; never substitute zero for unavailable correlations. <!-- sdd-owner: implementation -->
- [ ] Triangulate against direct numerical references, singleton/constant ROIs, insufficient samples, weighted-score cases, and non-finite inputs; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_aggregation.py tests/test_concept_fidelity.py tests/test_concept_anatomy.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for latent/concept predictive metrics, top-1 agreement/disagreement, JS divergence, consistency-loss direction, per-class disagreement counts, and separation from concept fidelity. <!-- sdd-owner: implementation -->
- [ ] Implement head-agreement metrics with fixed class order and explicit probability handling. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for fold/seed ROI profiles, pairwise Spearman correlation, mean pairwise correlation, per-ROI standard deviation, configured top-k Jaccard, and rank dispersion. <!-- sdd-owner: implementation -->
- [ ] Implement ROI stability using the terms `attention profile`, `concept profile`, and `ROI stability`; reject causal-importance, biomarker, disease-mechanism, and equivalent causal terminology in generated contracts. <!-- sdd-owner: implementation -->
- [ ] Implement descriptive CN/MCI/AD concept, `c_target`, and `g_bar` profiles with class support and subject-level bootstrap hooks; do not add unrestricted ROI-by-ROI inference. <!-- sdd-owner: implementation -->
- [ ] Triangulate with hand-computed JS/agreement values, one-instance stability behavior, top-k configuration validation, empty-class handling, and terminology assertions; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_agreement.py tests/test_concept_stability.py tests/test_concept_class_profiles.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests proving reuse of Phase 15 subject-level stratified bootstrap with explicit seed, replicate accounting, no ROI/fold-level resampling, and deterministic results. <!-- sdd-owner: implementation -->
- [ ] Implement paired subject comparisons for `prototype_pseudo` versus `source_only`, `coral`, `mmd`, and `cdan` across concept MAE, anatomy MAE, and JS divergence. <!-- sdd-owner: implementation -->
- [ ] Implement Holm correction separately by direction, checkpoint policy, and metric family with exactly four PADA comparator slots; exclude AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [ ] Generate all required machine-readable tables with ROI-indexed vectors and all required figures using fixed ROI order and predeclared top-k values, without favorable-ROI selection or intervention figures. <!-- sdd-owner: implementation -->
- [ ] Triangulate bootstrap invalid/unavailable replicate accounting, paired-subject alignment, Holm reference results, complete output names, and deterministic figure/table fixtures; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [ ] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [ ] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->
- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Current apply invocation — WU-04 completed

**status:** completed for the assigned WU-04 / T-16-04 slice. Subject aggregation, concept fidelity, and anatomical consistency behavior were implemented and focused verification passed. Work remained limited to the WU-04 production and test paths; no review, receipt, branch, commit, pull request, or delivery gate was started.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `both` / hybrid session; OpenSpec is authoritative because `openspec/` exists
- `applyState`: `ready` before this slice; remaining implementation work exists
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress`: 14 of 63 implementation rows complete before this slice; 21 of 63 complete after this slice
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-04 / T-16-04 only; WU-05 and later remain deferred to subsequent chain slices.
- No size exception was used; this slice stayed within the assigned work-unit boundary.
- Native receipt #1793 remains a parent-owned administrative delivery blocker.

### Completed tasks and persisted checkbox updates

The seven WU-04 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` after the corresponding work completed:

- Added RED coverage for source OOF uniqueness, fold ensembles, fold-then-seed aggregation, per-seed retention, direction separation, and immutable targets.
- Enforced common aggregation axes so transfer directions cannot be pooled; retained fold and seed aggregation semantics.
- Verified global, per-subject, and per-ROI fidelity metrics.
- Verified unweighted anatomy metrics remain separate from the canonical weighted score.
- Propagated explicit correlation availability reasons without zero substitution, with insufficient-sample precedence.
- Triangulated direct references, singleton/constant ROIs, insufficient samples, weighted cases, and invalid inputs.
- Ran the required focused verification command.

### Files changed

- `src/pada3dacb/evaluation/concepts/aggregation.py` — validate non-empty unique axes and reject mixed method/direction/checkpoint aggregation.
- `src/pada3dacb/evaluation/concepts/fidelity.py` — classify finite correlation availability with insufficient-sample precedence.
- `src/pada3dacb/evaluation/concepts/anatomy.py` — apply the same explicit correlation status ordering.
- `tests/test_concept_aggregation.py` — add mixed-direction and immutable-anatomy-target coverage.
- `tests/test_concept_fidelity.py` — add singleton and direct per-ROI reference coverage.
- `tests/test_concept_anatomy.py` — add singleton and constant-ROI coverage.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the seven WU-04 implementation rows complete.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- RED focused run: 4 expected failures for mixed-direction aggregation and insufficient-sample reason precedence.
- GREEN focused run: 23 passed.
- Triangulation focused run: 26 passed.
- Required focused verification: 26 passed; one Windows pytest cache-permission warning.
- Targeted Ruff check: PASS.
- `git diff --check` for WU-04 paths: PASS.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| WU-04 aggregation | `tests/test_concept_aggregation.py` | Unit | ✅ 6 baseline tests | ✅ 2 direction tests written and failed | ✅ 23 focused tests passed | ✅ immutable anatomy target and fold/seed cases | ✅ shared axis validation helper |
| WU-04 fidelity | `tests/test_concept_fidelity.py` | Unit | ✅ 4 baseline tests | ✅ insufficient-sample test written and failed | ✅ focused tests passed | ✅ direct per-ROI and constant/singleton cases | ✅ correlation check ordering |
| WU-04 anatomy | `tests/test_concept_anatomy.py` | Unit | ✅ 5 baseline tests | ✅ insufficient-sample test written and failed | ✅ focused tests passed | ✅ weighted, constant, singleton, and non-finite cases | ✅ correlation check ordering |

### Deviations from design

No scientific scope deviation. The implementation added an explicit guard that aggregation inputs share method, transfer direction, checkpoint, and domain axes; this is required to prevent cross-direction pooling. Correlation status now checks finite values and sample count before constant-value classification so singleton ROIs report `insufficient_samples` deterministically.

### Remaining tasks

The following unchecked persisted task lines remain and are deferred to later work units or the parent lifecycle:
- [ ] Add RED tests for latent/concept predictive metrics, top-1 agreement/disagreement, JS divergence, consistency-loss direction, per-class disagreement counts, and separation from concept fidelity. <!-- sdd-owner: implementation -->
- [ ] Implement head-agreement metrics with fixed class order and explicit probability handling. <!-- sdd-owner: implementation -->
- [ ] Add RED tests for fold/seed ROI profiles, pairwise Spearman correlation, mean pairwise correlation, per-ROI standard deviation, configured top-k Jaccard, and rank dispersion. <!-- sdd-owner: implementation -->
- [ ] Implement ROI stability using the terms `attention profile`, `concept profile`, and `ROI stability`; reject causal-importance, biomarker, disease-mechanism, and equivalent causal terminology in generated contracts. <!-- sdd-owner: implementation -->
- [ ] Implement descriptive CN/MCI/AD concept, `c_target`, and `g_bar` profiles with class support and subject-level bootstrap hooks; do not add unrestricted ROI-by-ROI inference. <!-- sdd-owner: implementation -->
- [ ] Triangulate with hand-computed JS/agreement values, one-instance stability behavior, top-k configuration validation, empty-class handling, and terminology assertions; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_agreement.py tests/test_concept_stability.py tests/test_concept_class_profiles.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add RED tests proving reuse of Phase 15 subject-level stratified bootstrap with explicit seed, replicate accounting, no ROI/fold-level resampling, and deterministic results. <!-- sdd-owner: implementation -->
- [ ] Implement paired subject comparisons for `prototype_pseudo` versus `source_only`, `coral`, `mmd`, and `cdan` across concept MAE, anatomy MAE, and JS divergence. <!-- sdd-owner: implementation -->
- [ ] Implement Holm correction separately by direction, checkpoint policy, and metric family with exactly four PADA comparator slots; exclude AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [ ] Generate all required machine-readable tables with ROI-indexed vectors and all required figures using fixed ROI order and predeclared top-k values, without favorable-ROI selection or intervention figures. <!-- sdd-owner: implementation -->
- [ ] Triangulate bootstrap invalid/unavailable replicate accounting, paired-subject alignment, Holm reference results, complete output names, and deterministic figure/table fixtures; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [ ] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [ ] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->
- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->
- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

### Skill resolution

`fallback-path`: no parent-injected `SKILL.md` path was provided. The global SDD status contract and strict-TDD support guidance were loaded. Strict TDD was followed because the parent phase context declared it active, despite the local `openspec/config.yaml` declaring `strict_tdd: false`.


### Post-persistence status re-read

Native `gentle-ai sdd-status phase-16-concept-validation --cwd . --json --instructions` confirmed:

- `artifactStore`: `openspec` (authoritative in the hybrid session)
- `taskProgress`: `total=65`, `completed=21`, `pending=44`, `allComplete=false`
- `applyState`: `ready`; `nextRecommended`: `apply`
- `dependencies.verify`: `blocked` until all implementation tasks complete
- `actionContext.mode`: `repo-local`; the repository root is the only allowed edit root

The cumulative apply-progress was also saved to Engram topic `sdd/phase-16-concept-validation/apply-progress`, and the Engram tasks observation was updated.

## Current apply invocation — WU-05 completed

**status:** completed for the assigned WU-05 / T-16-05 slice. Head agreement, ROI stability, and class-conditional profile contracts were implemented and focused verification passed. Work remained limited to the WU-05 production and test paths; no review, receipt, branch, commit, pull request, or delivery gate was started.

### Structured status consumed / produced

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec is authoritative because `openspec/` exists)
- `applyState`: `ready` before and after this slice; remaining implementation work exists
- `taskProgress`: 21 of 65 complete before this slice; 28 of 65 complete after persisted checkbox updates
- `dependencies.apply`: `ready`; `dependencies.verify`: `blocked` until all implementation tasks complete
- `nextRecommended`: `apply`
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-05 / T-16-05 only; WU-06 and later remain deferred to subsequent chain slices.
- Slice diff: 144 additions and 6 deletions across the assigned production/test paths; below the 400-line review budget. No size exception was used.
- Native receipt #1793 remains a parent-owned administrative delivery blocker. No branch, tracker PR, child PR, commit, review actor, receipt, or delivery gate was created.

### Completed tasks and persisted checkbox updates

The seven WU-05 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion:

- Added RED coverage for predictive head metrics, top-1 agreement/disagreement, JS divergence, consistency direction, per-class disagreement, and separation from fidelity.
- Implemented fixed-class probability and label validation; validated the per-class disagreement-count helper under the fixed CN/MCI/AD order without changing shared schemas.
- Added RED coverage for fold/seed ROI profiles, Spearman stability, pairwise means, per-ROI dispersion, configured top-k Jaccard, and rank dispersion.
- Added explicit non-causal stability terminology and profile validation, preserving attention-profile/concept-profile/ROI-stability wording.
- Implemented descriptive CN/MCI/AD class profiles with finite, same-width subject-level inputs and deterministic bootstrap hooks.
- Triangulated hand-computed agreement/JS values, one-instance and invalid-profile stability behavior, top-k validation, zero-support handling, and terminology assertions.
- Ran and passed the required focused verification command.

### Files changed

- `src/pada3dacb/evaluation/concepts/agreement.py` — fixed class-order validation, vector-shape validation, and per-class disagreement handling.
- `src/pada3dacb/evaluation/concepts/stability.py` — added non-causal terminology contract and rank-dispersion input validation.
- `src/pada3dacb/evaluation/concepts/class_profiles.py` — added finite/same-width subject profile validation and bootstrap input validation.
- `tests/test_concept_agreement.py` — added RED/GREEN/triangulation coverage for integrated disagreement and fixed labels.
- `tests/test_concept_stability.py` — added invalid-profile and terminology coverage.
- `tests/test_concept_class_profiles.py` — added mixed-width and non-finite input coverage.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the seven WU-05 implementation rows complete; parent-owned rows preserved.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- Safety net before editing: required focused baseline passed, `14 passed`.
- RED run: `6 failed, 14 passed`; failures covered integrated per-class disagreement, fixed label validation, rank-profile validation/terminology, and class-profile input guards.
- GREEN run: required focused suite passed, `21 passed`.
- Triangulation/refactor run: `python -m pytest tests/test_concept_*.py -q --basetemp=artifacts/pytest-tmp-phase16` passed, `223 passed`, one Windows pytest cache-permission warning.
- Focused Ruff check: PASS.
- `git diff --check` for WU-05 paths: PASS.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Head agreement | `tests/test_concept_agreement.py` | Unit | ✅ 14 passed | ✅ 6 expected failures | ✅ 21 focused passed | ✅ analytic JS, zero-support, invalid labels, mismatched vectors | ✅ integrated per-class result and explicit validation |
| ROI stability | `tests/test_concept_stability.py` | Unit | ✅ 14 passed | ✅ expected profile/terminology failures | ✅ focused passed | ✅ reverse ranks, constant profile, one-instance behavior, invalid k | ✅ shared profile validation |
| Class profiles | `tests/test_concept_class_profiles.py` | Unit | ✅ 14 passed | ✅ mixed-width/non-finite failures | ✅ focused passed | ✅ deterministic bootstrap, zero support, malformed vectors | ✅ reusable record/bootstrap validation |

### Deviations from design

No scientific scope deviation. The implementation tightened the existing design by validating per-class disagreement inputs, rejecting labels outside fixed CN/MCI/AD order, rejecting malformed/non-finite profile inputs before aggregation, and exposing the required non-causal terminology contract. No training, adaptation, target-label use, concept/Jacobian recomputation, Phase 17, or real-data evaluation paths were changed.

### Remaining unchecked task rows

- [ ] Add RED tests proving reuse of Phase 15 subject-level stratified bootstrap with explicit seed, replicate accounting, no ROI/fold-level resampling, and deterministic results. <!-- sdd-owner: implementation -->
- [ ] Implement paired subject comparisons for `prototype_pseudo` versus `source_only`, `coral`, `mmd`, and `cdan` across concept MAE, anatomy MAE, and JS divergence. <!-- sdd-owner: implementation -->
- [ ] Implement Holm correction separately by direction, checkpoint policy, and metric family with exactly four PADA comparator slots; exclude AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [ ] Generate all required machine-readable tables with ROI-indexed vectors and all required figures using fixed ROI order and predeclared top-k values, without favorable-ROI selection or intervention figures. <!-- sdd-owner: implementation -->
- [ ] Triangulate bootstrap invalid/unavailable replicate accounting, paired-subject alignment, Holm reference results, complete output names, and deterministic figure/table fixtures; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [ ] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [ ] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->
- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->
- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-06 completed

**status:** completed for the assigned WU-06 / T-16-06 slice. The implementation stayed within the statistics, figures, tables, and focused-test ownership boundary. Delivery strategy `auto-chain` and chain strategy `feature-branch-chain` were consumed; no branch, commit, pull request, review actor, receipt, or delivery gate was started.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec is authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended` before apply: `apply`
- `taskProgress`: 28 of 65 complete before WU-06; 34 of 65 complete after WU-06
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-06 / T-16-06 only; WU-07 and later remain deferred.
- WU-06 changed-line slice: 345 additions-plus-deletions across implementation and focused tests; under the 400-line work-unit ceiling.
- Native receipt #1793 remains a downstream administrative delivery blocker. No delivery lifecycle action was taken.

### Completed tasks and persisted checkbox updates

All six WU-06 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion:

- Phase 15 subject-level stratified bootstrap reuse with explicit seed, replicate accounting, and deterministic RED coverage.
- Paired subject comparisons for prototype_pseudo against the four eligible PADA comparators across concept MAE, anatomy MAE, and JS divergence.
- Four-slot Holm correction for the concept metric family.
- Complete required table/figure output contracts with fixed ROI order and predeclared top-k validation.
- Triangulation for invalid/unavailable bootstrap cases, paired alignment, Holm references, output names, and deterministic fixtures.
- Focused verification command.

### Files changed

- `src/pada3dacb/evaluation/concepts/statistics.py`
- `src/pada3dacb/evaluation/concepts/figures.py`
- `src/pada3dacb/evaluation/concepts/tables.py`
- `tests/test_concept_statistics.py`
- `tests/test_concept_figures.py`
- `tests/test_concept_tables.py`
- `openspec/changes/phase-16-concept-validation/tasks.md`
- `openspec/changes/phase-16-concept-validation/apply-progress.md`

### Verification evidence

- Safety-net baseline: focused WU-06 suite passed, 11 tests.
- RED: four new contract tests failed before production implementation (sampler reuse, paired comparisons, complete figures, complete tables).
- GREEN: focused WU-06 suite passed, 15 tests.
- TRIANGULATE: statistics reference and edge-case suites passed with the focused suite, 20 tests total; single-subject invalid replicate accounting, comparator exclusion, fixed-class bootstrap, paired alignment, Holm references, and deterministic output fixtures are covered.
- REFACTOR: extracted the ordered concept metric contract, ran Ruff on all WU-06 implementation/tests, and re-ran the focused suite.
- `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16` — **15 passed**.
- Extended focused run including `tests/test_concept_statistics_reference.py` and `tests/test_concept_statistics_edge_cases.py` — **20 passed**.
- `python -m ruff check` on all WU-06 implementation and test files — PASS.
- `git diff --check` on all WU-06 paths — PASS.
- Pytest emitted one pre-existing Windows cache-permission warning; no test failed.

### TDD Cycle Evidence

| Task slice | Test files | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---:|---|---|---|---|
| WU-06 statistics, figures, and tables | `tests/test_concept_statistics.py`, `tests/test_concept_figures.py`, `tests/test_concept_tables.py` | 11 passed | 4 failing contract tests written first | 15 passed | 20 passed with reference/edge cases | Ruff and focused tests passed |

### Deviations from design

No scope deviation. The existing concept statistics now delegates subject index generation to the Phase 15 bootstrap sampler. New orchestration helpers preserve four approved comparator slots, fixed metric-family correction, complete required table headers, and the five fixed figure names without selecting favorable ROIs or adding intervention figures.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [ ] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [ ] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->
- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks (exact persisted unchecked lines)

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-07 completed

**status:** completed for WU-07 / T-16-07. Added independent mathematical reference coverage and read-only inference boundary checks only. The requested delivery path `auto-chain` with `feature-branch-chain` was consumed; this executor did not create branches, commits, pull requests, review actors, receipts, or delivery gates.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`
- `dependencies.apply`: `ready`
- `nextRecommended`: `apply`
- `taskProgress` before WU-07: 34 of 65 complete; after WU-07: 38 of 65 complete
- `actionContext.mode`: `repo-local`
- `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`
- `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]
- `actionContext.warnings`: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-07 / T-16-07 only; WU-08 and later remain deferred.
- Changed-line slice: 269 additions-plus-deletions across the three assigned test files; below the 400-line ceiling. No size exception was used.
- Native receipt #1793 remains a parent-owned administrative delivery blocker. No delivery lifecycle action was taken.

### Completed tasks and persisted checkbox updates

All four WU-07 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after completion:

- Added independent MAE/RMSE/bias/correlation, weighted anatomy, JS divergence, fold-then-seed aggregation, subject bootstrap, and four-slot Holm references.
- Added constant-ROI, insufficient-sample, numerical-failure, missing-class, unavailable-metric, and paired-vector mismatch edge cases.
- Verified synthetic inference uses precomputed targets under `torch.no_grad()` without optimizer, backward, step, or target regeneration behavior; parameters remained unchanged.
- Ran the assigned focused verification command with no mathematical discrepancies.

### Files changed

- `tests/test_concept_metrics_reference.py`
- `tests/test_concept_statistics_edge_cases.py`
- `openspec/changes/phase-16-concept-validation/tasks.md`
- `openspec/changes/phase-16-concept-validation/apply-progress.md`

`tests/test_concept_statistics_reference.py` was included in the assigned focused command and remained unchanged because its existing independent references already covered the requested bootstrap and Holm behavior.

### Verification evidence

- Safety-net baseline before editing existing WU-07 test files: `python -m pytest tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` — **5 passed**.
- Focused WU-07 command: `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` — **15 passed**.
- `python -m ruff check tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py` — **PASS**.
- `git diff --check` on assigned test paths — **PASS**.
- Pytest emitted one pre-existing Windows cache-permission warning; no test failed.

### TDD Cycle Evidence

| Task slice | Test files | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---:|---|---|---|---|
| Independent mathematical references | `tests/test_concept_metrics_reference.py` | N/A (new coverage) | Independent assertions written before focused execution; no production code was required | 7 tests passed | Direct numerical equations, two seeds/folds, subject-stratified bootstrap, and Holm ties passed | Ruff and focused tests passed |
| Edge-case verification | `tests/test_concept_statistics_edge_cases.py` | 5 passed | Edge assertions written before focused execution | 3 new edge tests passed | Numerical failure, missing class support, and mismatched paired vectors passed alongside existing constant/insufficient/unavailable cases | Ruff and focused tests passed |
| Read-only inference boundary | `tests/test_concept_metrics_reference.py` | N/A (new coverage) | Boundary test written before focused execution | Parameter immutability/no-grad assertions passed | Static forbidden-operation checks and precomputed-target preservation passed | No production refactor required |

### Test Summary

- **Total tests written:** 10
- **Total tests passing:** 15 in the assigned focused command
- **Layers used:** Unit (15); Integration (0); E2E (0)
- **Approval tests:** None — no refactoring task
- **Pure functions created:** 2 independent reference helpers (`_pearson`, `_spearman`)

### Deviations from design

No production code or prohibited training/adaptation paths were changed. Existing `tests/test_concept_statistics_reference.py` already contained independent bootstrap and Holm checks, so WU-07 strengthened coverage through the new mathematical reference file and edge-case additions rather than duplicating those tests.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [ ] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [ ] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [ ] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [ ] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [ ] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->


## Latest apply invocation — WU-08 completed

**status:** completed for WU-08 / T-16-08. Strengthened report/CLI behavior with case-insensitive direction parsing, validate-only statistics isolation, manifest-last output planning, and safe overwrite rejection for unknown paths. Delivery path `auto-chain`; chain strategy `feature-branch-chain`. No branches, commits, PRs, review actors, receipts, or delivery gates were created.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`; `dependencies.apply`: `ready`; `nextRecommended`: `apply`
- `taskProgress`: 38 of 65 before WU-08; 45 of 65 after WU-08
- `actionContext`: `repo-local`; workspace and allowed edit root: `C:/Users/LOQ/Desktop/PADA-3DACB`; warnings: none

### Workload / PR boundary

WU-08 / T-16-08 only. The assigned code/test slice changed 90 additions-plus-deletions, below the 400-line ceiling; no size exception. WU-09 and later remain deferred. Native receipt #1793 remains a parent-owned administrative delivery blocker.

### Completed tasks and persisted checkbox updates

All seven WU-08 implementation-owned rows in `tasks.md` are persisted as `- [x]`. Existing orchestration, configuration, exports, and real-run gate behavior were covered; new tests cover the full CLI control selection, uppercase direction spelling, validate-only no-statistics boundary, manifest ordering, and unknown-path overwrite rejection.

### Files changed

- `scripts/evaluate_concepts.py`
- `src/pada3dacb/evaluation/concepts/report.py`
- `tests/test_concept_cli.py`
- `tests/test_concept_modes.py`
- `tests/test_concept_report.py`
- `openspec/changes/phase-16-concept-validation/tasks.md`
- `openspec/changes/phase-16-concept-validation/apply-progress.md`

### Verification evidence

- RED focused command: 4 expected failures exposed the four corrected behaviors.
- GREEN focused command: `python -m pytest tests/test_concept_cli.py tests/test_concept_report.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tmp-phase16` — 18 passed.
- Triangulation: `python -m pytest tests/test_concept_integration.py tests/test_concept_regressions.py tests/test_concept_report.py tests/test_concept_cli.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tmp-phase16` — 22 passed.
- Ruff and `git diff --check` passed on assigned paths. Pytest emitted only the pre-existing Windows cache-permission warning.

### TDD Cycle Evidence

| Task slice | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| CLI controls/direction | 4 passed | Expected parser failure | 18 focused passed | Both directions, sensitivity, overwrite, bootstrap, device | Ruff passed |
| Validate-only boundary | 8 passed | Expected statistics-call failure | 18 focused passed | Dry-run and evaluate remained covered | No behavior refactor |
| Atomic report safety | 6 passed | 2 expected report failures | 18 focused passed | Deterministic bundle/reuse/tamper tests | Ruff/diff passed |

### Deviations from design

None. The plan is now sorted with `evaluation_manifest.json` explicitly last, and overwrite fails closed rather than deleting unknown user files.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [ ] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [ ] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [ ] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->
- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->
- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-09 completed

**status:** completed for WU-09 / T-16-09. Added a deterministic synthetic fixture matrix, strengthened complete synthetic integration coverage, and added adaptation/causal/Phase 17 boundary protection. Delivery path `auto-chain`; chain strategy `feature-branch-chain`. No branches, commits, PRs, review actors, receipts, or delivery gates were created.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`; `dependencies.apply`: `ready`; `nextRecommended`: `apply`
- `taskProgress`: 45 of 65 before WU-09; 50 of 65 after WU-09
- `actionContext`: `repo-local`; workspace and allowed edit root: `C:/Users/LOQ/Desktop/PADA-3DACB`; warnings: none

### Workload / PR boundary

- Current boundary: WU-09 / T-16-09 only; WU-10 and later remain deferred.
- Changed slice: 104 additions-plus-deletions, below the 400-line ceiling; no size exception.
- Native receipt #1793 remains a parent-owned administrative delivery blocker.

### Completed tasks and persisted checkbox updates

All five WU-09 implementation-owned rows in `tasks.md` are persisted as `- [x]`: deterministic fixture coverage; integration mode/output coverage; scientific and phase-boundary protection; method/regression coverage; and the required focused verification command.

### Files changed

- `tests/phase16_integration_fixtures.py` — added the configured two-direction, five-fold, one-seed, primary/sensitivity, eligible-method and not-applicable-method matrix.
- `tests/test_concept_integration.py` — validates manifest identity, exact output plan, required tables/figures, statuses, and fixture-matrix boundary behavior.
- `tests/test_concept_boundaries.py` — rejects forbidden adaptation-loader, Jacobian, causal, biomarker, disease-mechanism, and Phase 17 tokens.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked five WU-09 implementation rows complete.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- Safety net before edits: the requested WU-09 suite passed 21 tests.
- RED: integration collection failed as expected before the new fixture module existed (`ModuleNotFoundError`).
- GREEN: integration suite passed 1 test, then 2 tests after matrix triangulation.
- Boundary focused run: 4 passed.
- Required WU-09 suite: `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16` — **23 passed**, one pre-existing Windows pytest cache-permission warning.
- Refactor checks: `python -m ruff check tests/phase16_integration_fixtures.py tests/test_concept_integration.py tests/test_concept_boundaries.py` — PASS; `git diff --check` — PASS.

### TDD Cycle Evidence

| Task slice | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Synthetic fixture matrix | 21 passed | Missing fixture import failed collection | 1 then 2 integration tests passed | Missing-fold configuration rejected | Ruff passed |
| Integration output contract | 21 passed | Missing fixture import failed collection | Complete matrix test passed | Exact output plan and statuses across directions/policies | Ruff/diff passed |
| Boundary protection | 21 passed | N/A: test-only boundary extension | 4 boundary tests passed | Forbidden-token scan covers alternate paths | Ruff/diff passed |
| Regression coverage | 21 passed | N/A: existing regression tests | 23 required tests passed | Both transfer directions, sensitivity, reuse, and all methods | Ruff/diff passed |

### Deviations from design

None. Production code, training/adaptation paths, Phase 17 paths, and real-data authorization were not changed.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [ ] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery blocker without overstating scientific results. <!-- sdd-owner: implementation -->
- [ ] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->
- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-10 completed

**status:** completed for WU-10 / T-16-10. Documentation now describes safe evaluator use, the synthetic-only boundary, scientific contracts and limitations, and the delivery restrictions. Delivery path `auto-chain`; chain strategy `feature-branch-chain`. No branches, commits, PRs, review actors, receipts, or delivery gates were created.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (hybrid session; OpenSpec authoritative because `openspec/` exists)
- `applyState`: `ready`; `dependencies.apply`: `ready`; `nextRecommended`: `apply`
- `taskProgress`: 50 of 65 before WU-10; 53 of 65 after WU-10
- `actionContext`: `repo-local`; workspace and allowed edit root: `C:/Users/LOQ/Desktop/PADA-3DACB`; warnings: none

### Workload / PR boundary

- Current boundary: WU-10 / T-16-10 only; WU-11 and later remain deferred.
- Changed slice: documentation-only edits, below the 400-line ceiling; no size exception.
- Native receipt #1793 remains a parent-owned administrative delivery blocker.

### Completed tasks and persisted checkbox updates

All three WU-10 implementation-owned rows in `tasks.md` are persisted as `- [x]`.

### Files changed

- `docs/CONCEPT_EVALUATION.md`
- `docs/PHASE16_REPORT.md`
- `docs/IMPLEMENTATION_AUDIT.md`
- `openspec/changes/phase-16-concept-validation/tasks.md`
- `openspec/changes/phase-16-concept-validation/apply-progress.md`

### Verification evidence

- Focused WU-09 integration/regression command: **23 passed**, one non-fatal Windows pytest cache-permission warning.
- Full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16-full`: timed out at 180 seconds; no pass claim is made.
- `python -m ruff check .`: PASS.
- `git diff --check`: PASS.
- Documentation audit confirms fixed `(CN, MCI, AD) = (0, 1, 2)` order, immutable `c_target`/`g_bar`, posthoc-only target labels, unavailable reasons, no causal claims, closed real gate, blocked CFS/ACS/PCS/QIS, and no Phase 17 work.

### Deviations from design

No implementation behavior changed. The full-suite timeout is recorded as incomplete evidence rather than treated as a success. Documentation explicitly limits claims to deterministic synthetic/read-only validation.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [ ] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [ ] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction. <!-- sdd-owner: implementation -->
- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Latest apply invocation — WU-11 completed

**status:** completed for WU-11 / T-16-11. The independent final audit is PASS WITH WARNINGS; no scientific blocker was found. Implementation code was not modified.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`; `dependencies.apply`: `ready`; `nextRecommended`: `apply`
- `taskProgress`: 53 of 65 before WU-11; 56 of 65 after WU-11
- `actionContext.mode`: `repo-local`; `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`; `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]; warnings: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Current boundary: WU-11 / T-16-11 only; WU-12 and WU-13 remain deferred.
- WU-11 changed only `specs/phase_16_concept_validation/final_audit.md`, within the `<=400` line boundary; no size exception.
- Native receipt #1793 remains a parent-owned administrative delivery blocker. No branch, commit, PR, review actor, receipt, or delivery gate was created.

### Completed tasks and persisted checkbox updates

The three WU-11 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after the audit completed:

- Audited scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work.
- Recorded PASS WITH WARNINGS and file-path evidence without modifying implementation.
- Required remediation of any future blocker before final validation and preserved the native receipt delivery restriction.

### Files changed

- `specs/phase_16_concept_validation/final_audit.md` — independent PASS WITH WARNINGS audit with file-path evidence.
- `openspec/changes/phase-16-concept-validation/tasks.md` — marked the three WU-11 implementation rows complete.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- `python -m pytest tests/test_concept_*.py -q --basetemp=artifacts/pytest-tmp-phase16-audit` — **238 passed**, one non-fatal Windows pytest cache-permission warning.
- WU-09 integration/regression command with the audit basetemp — **23 passed**, one non-fatal Windows pytest cache-permission warning.
- `python -m ruff check .` — PASS.
- `git diff --check` — PASS.
- `python -m pip install -e .` — PASS; `pada3dacb==0.1.0` installed.
- `python -c "import pada3dacb; print(pada3dacb.__version__)"` — PASS; `0.1.0`.
- Configuration/output-plan audit — PASS for fixed class order, closed real gate, expected folds/seeds/top-k, 11 required tables, and 5 required figures.
- Scope and terminology audit — PASS; no protected training/adaptation/data/experiment/Phase 17 path changed and no forbidden causal terminology in the concept production package.
- Task ownership-marker audit — PASS; no malformed markers.
- Real-config dry-run without candidate inputs returned configuration error (expected missing-candidate behavior); validate-only returned gate-blocked (expected unresolved real gates). Neither command evaluated real data or wrote a result tree.

### TDD Cycle Evidence

This is a report-only audit task; no production behavior or implementation code was changed.

| Task slice | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Scientific/provenance/boundary audit | 238 concept tests + 23 integration/regression tests passed | N/A: no new production behavior; audit artifact only | Audit checks and focused suites passed | Independent equations, aggregation, boundary, configuration, output-plan, ownership, Ruff, and diff checks passed | N/A: no implementation refactor |
| Evidence/disposition report | Existing audit artifact read before replacement | N/A: structural report task | New file-path evidence recorded | Warnings separated from scientific blockers and delivery restriction | N/A: report-only |

### Deviations from design

No implementation deviation. The prior report's unsupported full-suite PASS claim was replaced with an evidence-accurate warning: WU-10 recorded the full-suite attempt as timed out, while the WU-11 focused and integration/regression suites passed. The native receipt restriction remains administrative and does not authorize delivery actions.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [ ] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results. <!-- sdd-owner: implementation -->
- [ ] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [ ] Confirm no repository bytes are changed by validation, no delivery action bypasses native receipt #1793, and the next phase is not started. <!-- sdd-owner: implementation -->
- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

## Current apply invocation — WU-09 already complete

**status:** no-op; the assigned WU-09 / T-16-09 slice was already completed and persisted before this invocation. No production or test edits were made, and no task checkbox required updating.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready`; `dependencies.apply`: `ready`; `nextRecommended`: `apply`
- `taskProgress`: 60 of 65 implementation-owned tasks complete; 5 pending
- `actionContext.mode`: `repo-local`; `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`; `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]; warnings: none

### Workload / PR boundary

- Delivery strategy: `auto-chain`
- Chain strategy: `feature-branch-chain`
- Assigned boundary: WU-09 / T-16-09 only; its five persisted implementation rows are already `- [x]`.
- Existing WU-09 evidence records 104 additions-plus-deletions, below the 400-line ceiling; no size exception.
- Native receipt #1793 remains a parent-owned administrative delivery blocker. No branch, commit, PR, review actor, receipt, or delivery gate was created.

### Verification evidence

- Existing cumulative evidence records the required WU-09 suite as **23 passed**, with a non-fatal Windows pytest cache-permission warning; no rerun was needed for this no-op invocation.
- Persisted `tasks.md` was re-read: all five WU-09 implementation-owned rows remain visibly marked `- [x]` and ownership markers are valid.

### Remaining implementation-owned tasks (exact persisted unchecked lines)

- [ ] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [ ] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [ ] Record the native receipt #1793 restriction as an administrative delivery blocker only; do not create branches, commits, or pull requests while it remains unresolved. <!-- sdd-owner: implementation -->

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

### Deviations from design

None. This invocation performed no implementation work because the requested work unit was already complete.

## Current apply invocation — WU-13 completed

**status:** completed for WU-13 / T-16-13. OpenSpec planning mirrors and the repository agent plan were synchronized without changing scientific or implementation artifacts.

### Structured status consumed

- `schemaName`: `gentle-ai.sdd-status`
- `changeName`: `phase-16-concept-validation`
- `artifactStore`: `openspec` (authoritative because `openspec/` exists)
- `applyState`: `ready` before this slice; implementation-owned work is complete after this slice and only parent-owned lifecycle rows remain.
- `taskProgress`: 60 of 65 before WU-13; 63 of 65 after WU-13, with 2 parent-owned rows deferred.
- `actionContext.mode`: `repo-local`; `workspaceRoot`: `C:/Users/LOQ/Desktop/PADA-3DACB`; `allowedEditRoots`: [`C:/Users/LOQ/Desktop/PADA-3DACB`]; warnings: none.

### Workload / PR boundary

- Delivery strategy: `auto-chain`.
- Chain strategy: `feature-branch-chain`.
- Current boundary: WU-13 / T-16-13 only; no scientific or production implementation paths were edited.
- WU-13 mirror edits were measured below the 400-authored-line ceiling; no size exception was used.
- Native receipt #1793 remains a parent-owned administrative delivery blocker. No branch, commit, PR, review actor, receipt, or delivery gate was created.

### Completed tasks and persisted checkbox updates

The three WU-13 implementation-owned rows in `openspec/changes/phase-16-concept-validation/tasks.md` were changed from `- [ ]` to `- [x]` immediately after the mirror synchronization and validation completed:

- Synchronized proposal, capability specification, design, tasks, and agent-plan mirrors with approved scope, ownership, dependencies, forecast, and blockers.
- Verified one owner per task path, complete work-unit boundaries, and prohibited training/Phase 17 paths.
- Recorded native receipt #1793 as an administrative delivery blocker only and preserved the no-branch/no-commit/no-PR restriction.

### Files changed

- `openspec/changes/phase-16-concept-validation/proposal.md` — added planning mirror ownership, delivery, and blocker boundary.
- `openspec/changes/phase-16-concept-validation/design.md` — added mirror and ownership constraints.
- `openspec/changes/phase-16-concept-validation/specs/phase-16-concept-validation/spec.md` — recorded capability mirror and delivery constraints.
- `openspec/changes/phase-16-concept-validation/tasks.md` — resolved auto-chain/feature-branch-chain metadata, corrected the capability mirror path, and marked WU-13 rows complete.
- `specs/phase_16_concept_validation/agent_plan.yaml` — corrected the capability mirror path, reconciled task state, and recorded WU-13 chain metadata.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Verification evidence

- RED structural contract check failed as expected on stale WU-13 metadata: missing WU-13 in the forecast, unresolved delivery strategy/chain strategy, stale capability path, and zeroed task state.
- GREEN mirror contract check: PASS; all five mirror paths exist, metadata is synchronized, 65 task rows are valid, 63 implementation rows are complete, and 2 parent rows remain deferred.
- Ownership validation: PASS; 14 actions, 66 owned paths, 0 duplicate paths.
- Work-unit boundary validation: PASS; all 13 units include `id`, `task`, `exact_paths`, `verification`, and `rollback`.
- `python -m pytest tests/test_concept_boundaries.py -q --basetemp=artifacts/pytest-tmp-phase16-wu13` — **4 passed**, one non-fatal Windows pytest cache-permission warning.
- Triangulated metadata validation: PASS for all five mirrors covering receipt #1793, feature-branch-chain, and Phase 17 restrictions.
- `git diff --check -- specs/phase_16_concept_validation/agent_plan.yaml` — PASS.

### TDD Cycle Evidence

This is a structural planning-mirror task; no production behavior or implementation code was changed.

| Task slice | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Mirror metadata synchronization | Existing planning artifacts read before edits | Structural contract failed on stale forecast, delivery, path, and task-state metadata | Mirror contract passed with 65 valid task rows and 63 implementation rows complete | All five mirrors checked for receipt, chain strategy, and Phase 17 restrictions | Re-ran YAML ownership/boundary checks after targeted edits; no further refactor needed |
| Ownership and boundary validation | Existing agent-plan ownership evidence | Stale capability path was detected by the RED contract | 14 actions / 66 owned paths / 0 duplicates; 13 units have complete boundaries | Alternate path and parent-marker cases validated | YAML remained parseable and diff check passed |

### Deviations from design

No scientific or implementation deviation. The stale OpenSpec capability path was corrected to the existing `specs/phase-16-concept-validation` mirror, and the task-state summary was reconciled to the persisted 63-complete / 2-parent-deferred state. No delivery action was taken.

### Remaining implementation-owned tasks

None. The persisted tasks artifact was re-read and all three WU-13 implementation rows are visibly marked `- [x]`.

### Deferred parent-owned lifecycle tasks

- [ ] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [ ] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; do not commit, push, open a PR, archive, or release while #1793 blocks delivery. <!-- sdd-owner: parent -->

### Skill resolution

`fallback-path`: no parent-injected `SKILL.md` path was available. The global SDD status and strict-TDD support guidance were loaded. CodeGraph MCP was unavailable after initialization status, so read-only filesystem inspection was used as the documented fallback. Strict-TDD evidence was recorded for this structural task; the authoritative `openspec/config.yaml` declares no project test runner.


## Current remediation invocation — verified Phase 16 blockers

**status:** partial; implementation blockers were repaired surgically, but Phase 16 remains blocked and is not complete.

### Scope and constraints

- No Phase 17 work, training/adaptation changes, review lifecycle command, branch, commit, push, PR, archive, release, or publication action was started.
- Existing Phase 16 changes and unrelated untracked files were preserved.
- Native receipt issue #1793 remains unresolved and parent-owned.
- Real ADNI/OASIS evaluation remains closed; validation uses a deterministic CPU-only synthetic checkpoint and one read-only inference batch.

### Files changed in this remediation

- `src/pada3dacb/evaluation/concepts/inference.py` — passes validated canonical `roi_masks` to `PADA3DACB.forward`; rejects missing, malformed, non-finite, empty, or incompatible-K masks; loads checkpoint state dicts strictly and raises an explicit compatibility error.
- `scripts/evaluate_concepts.py` — synthetic `--validate-only` now creates and strictly loads one deterministic checkpoint, runs one CPU no-grad model batch with ROI masks, and validates the returned subject record.
- `src/pada3dacb/evaluation/concepts/aggregation.py` — rejects observed seeds that differ from configured seeds even when only one seed is expected.
- `tests/test_concept_inference.py` — regression coverage for ROI-mask forwarding/validation and strict checkpoint compatibility.
- `tests/test_concept_aggregation.py` — regression coverage for an unexpected single seed.
- `tests/test_concept_modes.py` — verifies synthetic validate-only executes the model contract without statistics or output artifacts.
- `.gga` — restored Python/scientific review file patterns and exclusions without changing the pre-existing provider/time edits.
- `openspec/config.yaml` — restored `rules`, `testing`, and `quality` as top-level YAML sections.
- `AGENTS.md` — removed only the known trailing space at line 929; scientific authorization text was not changed.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this merged record.
- `openspec/changes/phase-16-concept-validation/verify-report.md`, `specs/phase_16_concept_validation/final_audit.md`, `sdd/phase-16-concept-validation/archive-report.md`, `verify-report.md` — reconciled to a truthful blocked state.

### Strict TDD evidence

- **RED:** `python -m pytest tests/test_concept_inference.py tests/test_concept_aggregation.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tmp-phase16-remediation-red` — 4 expected failures: strict loading was permissive, ROI masks were not required/forwarded, unexpected single seeds were accepted, and synthetic validate-only was a no-op (exit 1).
- **GREEN:** `python -m pytest tests/test_concept_inference.py tests/test_concept_aggregation.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tmp-phase16-remediation-green` — 35 passed, one non-fatal Windows pytest cache-permission warning (exit 0).
- **TRIANGULATE:** strict incompatibility, missing ROI masks, unexpected single seed, deterministic checkpoint loading, no-output validation, and synthetic subject-record contract cases passed in the focused GREEN run.
- **REFACTOR:** `python -m py_compile src/pada3dacb/evaluation/concepts/inference.py scripts/evaluate_concepts.py src/pada3dacb/evaluation/concepts/aggregation.py` — PASS (exit 0); `git diff --check` on remediation paths — PASS.

### Full-suite limitation

The prior full `python -m pytest -q` attempt timed out at 180 seconds. This is not a pass claim. The full-suite validation task remains unresolved/blocked; no task or artifact below treats the timeout as successful completion.

### Task and lifecycle reconciliation

- The two parent-owned lifecycle rows in `tasks.md` remain visibly unchecked.
- Implementation task checkboxes are not promoted beyond the evidence available here; Phase 16 is not declared complete.
- Verification and archive artifacts are blocked by the unresolved receipt #1793, the prior full-suite timeout, and the need for parent-owned lifecycle validation.

### Remaining blockers

1. Native review/receipt state for #1793 is still missing/unresolved; parent must restore native receipt authority before lifecycle actions.
2. Full repository validation has no successful completion evidence because the prior run timed out.
3. Real evaluation and manuscript scores CFS/ACS/PCS/QIS remain scientifically blocked by their existing authorization/equation gates.

### Next recommended action

Parent-owned blocked-state review/receipt recovery and a separately authorized validation decision; do not start Phase 17.

### Task artifact note

`openspec/changes/phase-16-concept-validation/tasks.md` retains the two parent-owned lifecycle rows as unchecked. Its full-suite validation row now explicitly records that the observed timeout is incomplete evidence, not a pass.

### Final focused validation update

- `python -m pytest tests/test_concept_inference.py tests/test_concept_aggregation.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_integration.py -q --basetemp=artifacts/pytest-tmp-phase16-remediation-final2` — **43 passed**, exit 0; one non-fatal Windows pytest cache-permission warning.
- Added malformed ROI-mask shape coverage; no deprecation warning remains.

- `python -m ruff check src/pada3dacb/evaluation/concepts/inference.py src/pada3dacb/evaluation/concepts/aggregation.py scripts/evaluate_concepts.py tests/test_concept_inference.py tests/test_concept_aggregation.py tests/test_concept_modes.py` — **All checks passed**, exit 0.

## Current remediation invocation — escalated Phase 16 review blockers

**status:** partial; introduced blockers from review lineage `review-6eaa5682ce08e7d6` were remediated, but the authoritative receipt remains `terminal_state=escalated` and Phase 16 remains blocked. This record is appended to the cumulative history; no prior apply-progress entry was overwritten.

### Scope and constraints

- No Phase 17 work, training/adaptation changes, review lifecycle command, new review budget, branch, commit, push, PR, archive, release, or publication action was started.
- Writes remained inside the exact parent-authorized source, test, and status/evidence paths.
- Scientific equations, target-label isolation, cohort support, real-data authorization, and phase authorization were preserved.
- The two parent-owned lifecycle task rows remain unchecked.

### Files changed in this remediation

- `src/pada3dacb/evaluation/concepts/statistics.py` — require subject identities or keyed metric mappings for method comparisons; reject metric/method ordering and set mismatches before paired bootstrap arithmetic.
- `src/pada3dacb/evaluation/concepts/discovery.py` — expose the specified not-applicable status for methods without a PADA-3DACB concept head.
- `src/pada3dacb/evaluation/concepts/inference.py` — accept canonical or equivalent batched ROI masks, collapse identical per-subject masks, and reject inconsistent masks.
- `scripts/evaluate_concepts.py` — allow configured predictive-only baselines in discovery selection and report not-applicable dry-run statuses without suppressing genuine failures.
- `tests/test_concept_statistics.py` — add keyed-identity, missing-identity, ordering, and subject-set safety tests.
- `tests/test_concept_discovery.py` — update the specified not-applicable status expectation.
- `tests/test_concept_inference.py` — move strict checkpoint compatibility coverage to collected scope and add batched/equivalence/inconsistency tests.
- `tests/test_concept_modes.py` — add real dry-run not-applicable output coverage.
- `openspec/changes/phase-16-concept-validation/verify-report.md` — reconcile to truthful BLOCKED state and current evidence.
- `openspec/changes/phase-16-concept-validation/sync-report.md` — reconcile stale PASS/archive claims to BLOCKED state.
- `specs/phase_16_concept_validation/final_audit.md` — record the remediated blocker controls.
- `response.json`, `verify-report.md`, `sdd/phase-16-concept-validation/archive-report.md`, `.artifacts/sdd/phase-16-concept-validation/verify-report.md` — reconcile candidate-created status artifacts to the authoritative timeout/escalation BLOCKED state.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this merged remediation record.

### Strict TDD evidence

- **RED:** `python -m pytest tests/test_concept_statistics.py tests/test_concept_inference.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tdd-remediation-red` — 7 failures observed, exit 1, before implementation (5 behavior failures plus 2 temporary test-import NameErrors corrected before GREEN). Failures covered keyed pairing, ordering/set safety, batched mask handling, and not-applicable dry-run behavior.
- **GREEN:** `python -m pytest tests/test_concept_statistics.py tests/test_concept_inference.py tests/test_concept_discovery.py tests/test_concept_modes.py -q --basetemp=artifacts/pytest-tdd-remediation-green2` — 50 passed, exit 0; one non-fatal Windows pytest cache-permission warning.
- **TRIANGULATE:** keyed mappings, unkeyed-array rejection, subject ordering/set mismatches, canonical masks, equivalent B>1 masks, inconsistent B>1 masks, strict checkpoint incompatibility, and real not-applicable dry-run output passed.
- **REFACTOR:** final Ruff, compile, and diff checks are recorded in the delegated handoff; no scientific equation or authorization behavior was changed.

### Blocker disposition

1. Scientific pairing safety: remediated with deterministic identity/order/set validation before the approved paired-bootstrap equations.
2. Real dry-run semantics: remediated; `not_applicable_no_pada3dacb_concept_head` is successful output, while genuine discovery/provenance issues remain configuration failures.
3. Batched ROI masks: remediated with safe collapse only for equivalent masks and deterministic rejection of inconsistent masks.
4. Strict checkpoint compatibility collection: remediated by moving the test out of the nested function.
5. Candidate-created status artifacts: reconciled to BLOCKED; no PASS or archive claim is manufactured, and the escalated receipt/timeout evidence is preserved.

### Unresolved blockers

- Review receipt `review-6eaa5682ce08e7d6` remains `terminal_state=escalated`; parent owns lifecycle handling.
- The prior full `python -m pytest -q` run timed out at 180 seconds; no full-suite pass is claimed.
- Parent-owned lifecycle rows remain unchecked; do not archive, commit, push, PR, release, or start Phase 17.
- Real evaluation remains closed and CFS/ACS/PCS/QIS remain blocked by existing scientific gates.

### Final remediation validation update

- `python -m pytest tests/test_concept_statistics.py tests/test_concept_discovery.py tests/test_concept_inference.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_integration.py -q --basetemp=artifacts/pytest-remediation-focused-final` — **58 passed**, exit 0; one non-fatal Windows pytest cache-permission warning.
- `python -m ruff check src/pada3dacb/evaluation/concepts/statistics.py src/pada3dacb/evaluation/concepts/discovery.py src/pada3dacb/evaluation/concepts/inference.py scripts/evaluate_concepts.py tests/test_concept_statistics.py tests/test_concept_discovery.py tests/test_concept_inference.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_integration.py` — **All checks passed**, exit 0.
- `python -m py_compile src/pada3dacb/evaluation/concepts/statistics.py src/pada3dacb/evaluation/concepts/discovery.py src/pada3dacb/evaluation/concepts/inference.py scripts/evaluate_concepts.py` — **PASS**, exit 0.
- `git diff --check -- <authorized remediation paths>` — **PASS**, exit 0.

## Current remediation invocation — RR-001 reference-contract escalation

**status:** blocked; the remaining introduced reference-test blocker RR-001 from native review lineage `review-0920fcca5828ef6` was remediated, but the native review escalation for issue #1793 remains unresolved. This entry is appended to the cumulative history; no prior apply-progress record was overwritten.

### Scope and constraints

- Edited only the explicitly authorized test, plan, task, and Phase 16 report paths.
- No Phase 17 work, review lifecycle command, branch, commit, push, PR, archive, release, or publication action was started.
- The two parent-owned lifecycle task rows remain unchecked.
- No implementation task completion was invented; current state remains 63 complete / 2 parent-owned open.

### Files changed in this remediation

- `tests/test_concept_metrics_reference.py` — added a valid canonical ROI mask, the two-argument `model(x, roi_masks)` probe contract, and a B>1 assertion while preserving reference mathematics.
- `tests/test_concept_inference.py` — moved strict checkpoint compatibility coverage to collected class-method scope.
- `specs/phase_16_concept_validation/agent_plan.yaml` — recorded BLOCKED status, 63 complete / 2 open task state, and the current escalated review lineage.
- `specs/phase_16_concept_validation/tasks.md` — recorded the blocked 63/2 state and removed the unsupported full-pytest completion mark.
- Phase 16 verification, audit, sync, archive, response, and artifact reports — reconciled to BLOCKED with current evidence and issue #1793 escalation.
- `openspec/changes/phase-16-concept-validation/apply-progress.md` — appended this cumulative record.

### Strict TDD evidence

- **RED:** `PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_inference.py -q -p no:cacheprovider` — 1 expected missing-ROI-mask failure, exit 1.
- **GREEN:** `PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_inference.py -q -p no:cacheprovider` — 27 passed, exit 0.
- **TRIANGULATE:** targeted negative/alternate contract command — 4 passed, exit 0; missing masks, inconsistent B>1 masks, incompatible checkpoints, and the B>1 reference probe were exercised.
- **REFACTOR:** focused Ruff, py_compile, and authorized `git diff --check` commands — exit 0.
- **Collection:** `PYTHONDONTWRITEBYTECODE=1 python -m pytest --collect-only -q -p no:cacheprovider tests/test_concept_inference.py` — 20 collected, exit 0.

### Validation limitation and blockers

- The prior full `python -m pytest -q` run timed out at 180 seconds; it remains incomplete evidence and is not represented as a pass.
- Native review lineage `review-0920fcca5828ef6` remains `terminal_state=escalated` on RR-001/evidence warnings under issue #1793.
- Parent-owned lifecycle validation remains pending; do not archive or begin Phase 17.

## Current remediation invocation — review-047ae7d944d9e975 blocker resolution

**status:** partial; the two introduced CRITICAL findings were remediated in the authorized Phase 16 implementation and test paths, but native review lineage `review-047ae7d944d9e975` remains escalated until the parent-owned lifecycle is resolved.

### Scope and constraints

- Preserved native review issue #1793 and Phase 16-only authorization.
- Did not start Phase 17, run review lifecycle commands, commit, push, PR, archive, release, or publication actions.
- Writes remained inside the exact delegated edit paths.
- Merged this entry with the complete prior apply-progress history; no prior entry was overwritten.

### Implemented controls

- `run_subject_inference` now obtains canonical atlas masks from the atlas artifact, prepares them with the existing feature-grid ROI preparation contract when needed, and rejects same-sized reordered masks before model inference.
- `compute_paired_method_comparisons` now rejects unkeyed diagnosis-label arrays and requires keyed labels in the canonical subject order; permuted and stale label keys fail deterministically.
- Synthetic report status rows now assign AAGN and FasterSNN exactly one not-applicable status and never emit an included duplicate for those methods.

### Strict TDD evidence

- **RED:** targeted blocker tests failed before implementation: 2 failures, exit 1; unkeyed labels and reordered ROI masks were not rejected.
- **GREEN:** focused blocker tests passed: 4 passed, exit 0.
- **TRIANGULATE:** focused Phase 16 suite passed: 66 passed, exit 0; collection reported 66 tests, exit 0; CLI/report, reference inference, keyed labels, permuted/stale labels, batched masks, and synthetic status paths were exercised.
- **REFACTOR:** Ruff, py_compile, and authorized diff checks passed, exit 0.

### Validation commands

- `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_concept_inference.py tests/test_concept_statistics.py tests/test_concept_metrics_reference.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_report.py tests/test_concept_integration.py` — 66 passed, exit 0.
- `PYTHONDONTWRITEBYTECODE=1 python -m pytest --collect-only -q -p no:cacheprovider tests/test_concept_inference.py tests/test_concept_statistics.py tests/test_concept_metrics_reference.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_report.py tests/test_concept_integration.py` — 66 collected, exit 0.
- `python -m ruff check src/pada3dacb/evaluation/concepts/inference.py src/pada3dacb/evaluation/concepts/statistics.py src/pada3dacb/evaluation/concepts/report.py scripts/evaluate_concepts.py tests/test_concept_inference.py tests/test_concept_statistics.py tests/test_concept_metrics_reference.py tests/test_concept_cli.py tests/test_concept_modes.py tests/test_concept_report.py tests/test_concept_integration.py` — all checks passed, exit 0.
- `python - <<'PY' ... py_compile.compile(..., cfile='/dev/null', doraise=True) ... PY` — passed, exit 0.
- `git diff --check -- <authorized Phase 16 paths>` — passed, exit 0.

### Task and blocker reconciliation

- `specs/phase_16_concept_validation/tasks.md` remains 63 complete / 2 open; exactly the two parent-owned lifecycle rows remain unchecked.
- The prior full pytest timeout remains incomplete evidence, not a pass.
- Remaining blocker: native review lineage `review-047ae7d944d9e975` is still escalated under #1793; parent owns lifecycle handling. Do not archive or start Phase 17.

## Current apply invocation — remaining executable tasks reconciled

**status:** partial/blocked for executor completion; no implementation-owned apply task remains. The authoritative executable task checkboxes are 63 complete and exactly 2 unchecked parent-owned lifecycle rows. The known RR-002 mirror discrepancy was resolved in favor of the executable task rows and their narrative ownership markers.

### Scope and constraints

- Read proposal, capability specification, design, tasks, configuration, and the complete cumulative apply history before making this determination.
- No production or test implementation task was legitimately available to this executor; therefore no task checkbox was changed.
- The two remaining unchecked rows are parent-owned review/receipt lifecycle actions and remain unchecked.
- No verify, archive, review lifecycle command, branch, commit, push, PR, release, or Phase 17 action was started.

### Task reconciliation

- `openspec/changes/phase-16-concept-validation/tasks.md` — 63/65 rows checked.
- Remaining unchecked rows: bounded implementation review and content-bound receipt validation, both marked `sdd-owner: parent` and blocked by native issue #1793.
- No implementation-owned task was invented or marked complete.

### Verification evidence

- Full concept subset command using the required WindowsApps interpreter and clean basetemp/cache:
  `C:\Users\LOQ\AppData\Local\Microsoft\WindowsApps\python.exe -m pytest tests/test_concept_*.py -q --basetemp=artifacts/pytest-tmp-apply --override-ini cache_dir=artifacts/.cache-apply`
  — **exit 1**, **311 passed, 1 failed**. The failure is `tests/test_concept_integration.py::test_complete_synthetic_method_direction_policy_matrix`, which returns configuration exit code 3 because the test copies the repository config into a temporary directory without supplying the required verified synthetic fixture-manifest fields.
- Exclusion run for that failure:
  `C:\Users\LOQ\AppData\Local\Microsoft\WindowsApps\python.exe -m pytest <all tests/test_concept_*.py files> -q -k "not complete_synthetic_method_direction_policy_matrix" --basetemp=artifacts/pytest-tmp-apply-excluding-known --override-ini cache_dir=artifacts/.cache-apply-excluding-known`
  — **exit 1**, **309 passed, 2 failed, 1 deselected**. The remaining failures are pre-existing synthetic output/reuse issues in `tests/test_concept_modes.py::test_synthetic_evaluate_and_read_only_reuse` and `tests/test_concept_report.py::test_synthetic_bundle_is_deterministic_manifest_last_and_reusable`.
- Checkbox count probe — **exit 0**, `TASK_COUNTS 63 2 65 PARENT_OPEN 2`.

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | Required concept subset: exit 1; 311 passed, 1 failed. Exclusion run: exit 1; 309 passed, 2 failed, 1 deselected. No implementation task was marked complete because the failures are outside an unchecked implementation row. |
| Runtime harness command/scenario and exact result | N/A for this invocation: no implementation-owned runtime boundary remains; runtime/lifecycle actions are parent-owned. |
| Rollback boundary | `openspec/changes/phase-16-concept-validation/apply-progress.md` only; no code or test behavior was changed. |

### TDD Cycle Evidence

No RED/GREEN/triangulation/refactor cycle was applicable: the executable task list contains no unchecked implementation task, and the remaining rows explicitly belong to the parent lifecycle. The concept tests were run as a safety/continuity check only; their failures were not silently repaired.

### Risks and blockers

- Native review lineage `review-047ae7d944d9e975` remains escalated under issue #1793; parent owns lifecycle handling.
- The concept subset is not fully green in this working tree. The specific failing tests above require a separately authorized remediation task; they were not assigned by the remaining executable task list.
- Real evaluation remains closed and CFS/ACS/PCS/QIS remain scientifically blocked by the existing authorization/equation gates.

### Next recommended action

Parent-owned lifecycle handling only: resolve the native receipt state and decide whether to authorize a separate remediation for the three failing synthetic tests. Do not run verify/archive/review from this executor and do not start Phase 17.

## Parent-owned remediation closure — integration test fixture-manifest fix

**status:** resolved; concept subset is fully green (312 passed, exit 0) with the WindowsApps interpreter and clean basetemp/cache.

### Root cause

`tests/test_concept_integration.py::test_complete_synthetic_method_direction_policy_matrix` was updated to use `fixture_matrix`/`build_concept_output_plan` but did not inject the verified synthetic fixture-manifest fields (`fixture_manifest_path`, `fixture_manifest_sha256`, `fixture_allowed_root`) that the post-remediation CLI requires in `_load_verified_fixture_manifest`. The CLI therefore returned `CONFIGURATION_ERROR` (exit 3) and the test failed at `assert code == ExitCode.SUCCESS`.

### Fix

Added `_write_fixture_config(config, tmp_path)` to `tests/test_concept_integration.py`, mirroring the existing `_fixture_config` pattern in `tests/test_concept_modes.py`: it writes a deterministic `fixture.bin`, builds a `phase16-concept-fixture-manifest-v1` manifest with the SHA-256 of the manifest bytes, and injects the three required config keys. The config keeps the full 5-fold `expected_folds` required by `fixture_matrix`.

### Verification evidence

- `C:\Users\LOQ\AppData\Local\Microsoft\WindowsApps\python.exe -m pytest tests/test_concept_integration.py -q --basetemp=artifacts/pytest-tmp-apply3 --override-ini cache_dir=artifacts/.cache-apply3` — **exit 0**, **2 passed**.
- Full concept subset (all `tests/test_concept_*.py`):
  `C:\Users\LOQ\AppData\Local\Microsoft\WindowsApps\python.exe -m pytest <all concept files> -q --basetemp=artifacts/pytest-tmp-apply4 --override-ini cache_dir=artifacts/.cache-apply4` — **exit 0**, **312 passed** in 129.29s.
- Isolated re-check of the two tests the executor flagged as additional failures:
  `python.exe -m pytest tests/test_concept_modes.py::test_synthetic_evaluate_and_read_only_reuse tests/test_concept_report.py::test_synthetic_bundle_is_deterministic_manifest_last_and_reusable -q --basetemp=artifacts/pytest-tmp-apply5 --override-ini cache_dir=artifacts/.cache-apply5` — **exit 0**, **2 passed** in 49.07s. Those two failures in the executor's exclusion run were transient interference from concurrent parent-side full-suite chunks (456/245 test blocks running in parallel), not code defects; they pass in isolation and in the full green subset.
- `python -m ruff check tests/test_concept_integration.py` — PASS (0 errors).
- `git diff --check` — PASS.

### Remaining blockers (unchanged)

- The two unchecked task rows remain parent-owned lifecycle rows (bounded implementation review and content-bound receipt validation), blocked by native review issue #1793.
- `select_lineage` capture for lineage `review-047ae7d944d9e975` remains an external parent/operator action; the CLI has no `select-lineage` subcommand and no installed documentation defines it, so the capture was not fabricated.
- Verify/archive remain blocked; Phase 17 was not started.

## Parent decision and investigation closure — reopen review from the start

**date:** 2026-08-06

**Status:** investigation closed; explicit maintainer decision recorded: **re-open with a NEW native review** (issue #1793), not lineage selection of the existing escalated lineage.

### Investigation verdict — `external.select_lineage` is unsupported on this host

The native `review.status` bootstrap for this working tree returns:

- `applicability: ambiguous`, `action: select_lineage`, `receipt.status: not_applicable`
- `next_transition.kind: collect`, `capture_operation: external.select_lineage` with arguments:
  - `target_identity: sha256:69d3b7f8fb40304f1f7264e38a6a21d4244e00e0d278cd8aabde8d1941276dfd`
  - `projection: workspace`, `base_tree: eaf310f02124314a1c13761bcf3487a05fced0dd`, `candidate_tree: 8646ca218762f19381bb123f18165036dee1de7d`
  - `candidates`: `review-047ae7d944d9e975`, `review-0920fcca5828ef6e`, `review-49ce22e28f7a8c5f`, `review-5b824f1df0404e43`, `review-6eaa5682ce08e7d6`

All locally installed candidates were probed and none implements `select-lineage`:

| Piece | Version | `select-lineage` |
|---|---|---|
| `gentle-ai.exe` (AppData\Local\gentle-ai\bin) | 2.1.11 | unknown review command |
| `gentle-ai.exe` (go\bin) | **2.2.4** | unknown review command |
| `gga` (C:\Users\LOQ\bin) | 2.10.1 | not a review-integration consumer |
| OpenCode `review-result-artifacts.ts` plugin | — | only captures `capture-result`/`preserve-result` for lenses; does not handle lineage selection |
| `pi` (npm @earendil-works/pi-coding-agent) | — | unrelated tool |

Per the lifecycle contract, the parent/agent must not fabricate the capture, must not hand-edit `review-state.json`, and must stop at `unsupported-capability` for an `escalated` lineage. The existing escalated lineage `review-047ae7d944d9e975` already has `review/complete-review` executed with `receipt_published: true` and `resolved_finding_ids: ["RISK-002"]` (corroborated), but `terminal_state: escalated` due to RISK-001 and RR-001.

### Maintainer decision — REOPEN with a new native review

Explicit human decision (user): resolve #1793 by opening a **fresh native review** of the working tree, not by reviving the escalated lineage. Rationale: the working tree has diverged from `review-047ae7d944d9e975` (new paths: `src/pada3dacb/evaluation/concepts/provenance.py`, `tests/test_concept_provenance.py`, `openspec/changes/phase-16-review-remediation/*`, provenance/`inference` hardening, `scripts/evaluate_concepts.py` remediation), and the escalated lineage is not selectable on this host.

Actions taken:
- `gentle-ai review start` run against the current working tree to open the **new** review (see next section for its result).
- This supersedes the earlier `select_lineage` decision; no manual edit of `review-state.json` or any transaction file was performed by an agent.

The previous escalated lineage remains `escalated`; it is preserved as historical record under `.git/gentle-ai/review-transactions/v2/review-047ae7d944d9e975/` and is not modified by this reopen.

### Next steps

- Record the `review/start` result (lenses selected, budget, new `lineage_id`) and run the selected reviewer lens(es) per the lifecycle contract.
- Mark the parent-owned rows in `tasks.md` only after the new review produces a valid receipt; do not fabricate.
- Verify/archive remain blocked until the reopened review yields `reviewGate.result: allow`.
- Phase 17 was not started.

## Reopened native review — `gentle-ai review start` result

**status:** created/resumed; new review LP **`review-020be3e98a00efe2`** is now `reviewing`.

### Start output (contract form)

| Field | Value |
|---|---|
| `operation` | `review.start` (action `resumed`) |
| `lineage_id` | `review-020be3e98a00efe2` |
| `state` | `reviewing` |
| `risk_level` | `medium` |
| `selected_lenses` | `["review-reliability"]` (order 0) |
| `projection` / `base_tree` | `workspace` / `eaf310f02124314a1c13761bcf3487a05fced0dd` |
| `candidate_tree` | `2909f0199dad9e7c97408bf22a461bed7f46b72c` |
| `changed_files` / `changed_lines` | 110 / 16700 |
| `correction_budget` | 200 |
| `target_identity` | `sha256:020be3e98a00efe2ea2df760d5a210a9b41c216cf247add13e227d484a30e877` |
| `risk_reasons` | `.gga` executable change |

The reopened review fixes a **single consolidated lens** (`review-reliability`) over the entire Phase 16 candidate — the risk classification is `medium`, not the previously frozen `high`. This re-validates RI-001/RI-002/RR-001 surface PLUS the remediation work present in this tree (`provenance.py`, `inference` hardening, `scripts/evaluate_concepts.py` remediation) that was introduced after the original escalated lineage. `review-047ae7d944d9e975` remains `escalated` as historical record and is not modified.

### Lens binding contract for the running review

- `GENTLE_AI_REVIEW_BINDING {"lineage":"review-020be3e98a00efe2","target":"sha256:020be3e98a00efe2ea2df760d5a210a9b41c216cf247add13e227d484a30e877","lens":"review-reliability","order":0}`
- Runner: `review-reliability` agent (foreground, exactly once). Capture handled by the installed OpenCode hook (`review-result-artifacts.ts`) via `gentle-ai review capture-result`.

The changed-path manifest (all 110 paths) is frozen in the `review/start` output above and must be appended to the lens prompt before execution; if it cannot be reproduced, the lens must stop.

## Reopened review — finalize result: APPROVED

**status:** `review/finalize` completed with **`state: approved`** for lineage `review-020be3e98a00efe2` (store revision `sha256:0592985f498c687a49b1a1bf90a2b91521178d94d48404d1215faff514418306`). Incident #1793 is resolved: the reopened review is the approved receipt.

### Reviewer outcome

The single consolidated lens `review-reliability` returned exactly **one WARNING** (non-blocking, `info` outcome):

| ID | Location | Severity | Claim |
|---|---|---|---|
| (none assigned) | `src/pada3dacb/evaluation/concepts/discovery.py:191` | WARNING | A syntactically valid but non-mapping checkpoint payload causes `AttributeError` at `checkpoint.get(...)` instead of returning a validation issue, producing an internal-error CLI result for malformed input. |

No BLOCKER and no CRITICAL findings. No correction transaction was required. The reopened review re-validated the full Phase 16 candidate PLUS the remediation work (`provenance.py`, `inference` hardening, `evaluate_concepts.py` fixture-manifest remediation) folded into this tree.

### Evidence bound at finalize

`artifacts/phase16-review-evidence.md`: full concept subset **312 passed** (exit 0, 129.29 s), focused integration **2 passed**, isolated reuse/determinism re-check **2 passed**, Ruff PASS, `git diff --check` PASS, scientific invariants confirmed.

### Next transition

`delivery_gate_required` — capture `external.select_gate` for lineage `review-020be3e98a00efe2`, expected revision `sha256:0592985f498c687a49b1a1bf90a2b91521178d94d48404d1215faff514418306`, target `sha256:020be3e98a00efe2ea2df760d5a210a9b41c216cf247add13e227d484a30e877`.

Then execute the native gate validation:
`gentle-ai review validate --gate <gate> --cwd <repo> --lineage review-020be3e98a00efe2`

The two parent-owned rows in `tasks.md` (bounded implementation review; content-bound receipt validation) are now eligible to be marked complete by the parent once the delivery gate is validated — not by any executor.
