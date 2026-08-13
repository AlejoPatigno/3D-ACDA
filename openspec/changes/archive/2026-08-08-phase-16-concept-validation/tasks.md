# Phase 16 — Concept Validation Tasks

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 2,000–4,000 authored lines across implementation, tests, configuration, and documentation |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | WU-01 → WU-02 → WU-03 → WU-04 → WU-05 → WU-06 → WU-07 → WU-08 → WU-09 → WU-10 → WU-11 → WU-12 → WU-13 |
| Delivery strategy | auto-chain; native receipt approved (lineage review-68e92d2ce0c5935ff68976f9f7d1f666f21ab800) with post-apply gate allow; #1793 incident resolved by the approved receipt |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

Each implementation work unit must stop before production edits if its forecast or actual additions plus deletions exceeds 400 lines. Measure the current slice before editing, keep tests with the behavior they protect, and split again rather than consuming an unapproved size exception.

## Scope and ownership boundaries

- Read-only evaluation only; do not modify `src/pada3dacb/training/**`, `src/pada3dacb/models/**`, `src/pada3dacb/losses/**`, `src/pada3dacb/adaptation/**`, `src/pada3dacb/data/**`, `configs/experiments/**`, `artifacts/runs/**`, or `specs/phase_17/**`.
- Preserve fixed class order `CN=0, MCI=1, AD=2`, target-label isolation, immutable concept/anatomy artifacts, and the `authorized: false` real-run gate.
- Treat `aagn` and `faster_snn` as `not_applicable_no_pada3dacb_concept_head`, never as failed methods.
- Keep CFS, ACS, PCS, and QIS blocked unless authoritative equations are verified; do not infer definitions from names.

## Dependency-ordered implementation work units

### WU-01 — Reconcile the executable scientific contract (`T-16-01`)

**Depends on:** Phase 15 closure and concept audit.  
**Paths:** `specs/phase_16_concept_validation/{requirements.md,design.md,tasks.md,acceptance.md,metric_protocol.md,output_schema.md,manuscript_extraction.md,decisions.md,agent_plan.yaml}`.

- [x] Extract and reconcile tensor contracts, aggregation rules, metric equations, provenance gates, output names, and manuscript-score dispositions across the Phase 16 specification files. <!-- sdd-owner: implementation -->
- [x] Record unresolved CFS/ACS/PCS/QIS definitions as `BLOCKED` and document the transparent metric fallback without inventing equations. <!-- sdd-owner: implementation -->
- [x] Verify ownership, dependency order, prohibited paths, and the under-400-line slice boundary in `specs/phase_16_concept_validation/agent_plan.yaml`. <!-- sdd-owner: implementation -->
- [x] Verify the specification set is internally consistent and all referenced paths exist before implementation begins. <!-- sdd-owner: implementation -->

**Rollback:** specification files only. **Finish evidence:** specification validation and ownership check recorded.

### WU-02 — Complete independent scientific review (`T-16-02`)

**Depends on:** WU-01.  
**Path:** `specs/phase_16_concept_validation/spec_review.md`.

- [x] Review the Phase 16 contract for invented score definitions, target-label leakage, incorrect subject aggregation, causal overclaiming, and missing unavailable-state handling. <!-- sdd-owner: implementation -->
- [x] Record PASS or blocking findings with evidence and explicitly confirm that real evaluation remains gated. <!-- sdd-owner: implementation -->
- [x] Do not start implementation work while `specs/phase_16_concept_validation/spec_review.md` contains an unresolved blocker. <!-- sdd-owner: implementation -->

**Rollback:** review file only. **Finish evidence:** `spec_review.md` is PASS.

### WU-03 — Implement schemas, discovery, dataset, provenance, and inference (`T-16-03`)

**Depends on:** WU-02.  
**Production paths:** `src/pada3dacb/evaluation/concepts/{__init__.py,schemas.py,dataset.py,discovery.py,provenance.py,inference.py}`.  
**Test paths:** `tests/{phase16_helpers.py,test_concept_schemas.py,test_concept_dataset.py,test_concept_discovery.py,test_concept_provenance.py,test_concept_inference.py}`.

- [x] Add RED tests for schema validation, canonical class/ROI contracts, candidate discovery, read-only dataset construction, provenance mismatch exclusion, and no-grad tensor extraction using deterministic CPU fixtures. <!-- sdd-owner: implementation -->
- [x] Implement typed concept-evaluation records and validation for tensor shapes, finiteness, normalized concept ranges, alpha normalization, class order, and canonical ROI order. <!-- sdd-owner: implementation -->
- [x] Implement configured-root checkpoint/artifact discovery for eligible PADA methods and explicit not-applicable statuses for AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [x] Implement read-only source-validation and target-evaluation dataset construction plus exact provenance/hash validation; reject missing or conflicting candidates without crashing the pipeline. <!-- sdd-owner: implementation -->
- [x] Implement CPU-default checkpoint loading and no-grad forward extraction for all required tensors without training imports, optimizer state, parameter updates, or normalizer/Jacobian recomputation. <!-- sdd-owner: implementation -->
- [x] Triangulate with invalid-shape, invalid-hash, non-finite, alpha-sum, target-partition, and gradient/parameter-immutability tests; then refactor only after focused tests pass. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_schemas.py tests/test_concept_dataset.py tests/test_concept_discovery.py tests/test_concept_provenance.py tests/test_concept_inference.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** discovery, inference, schemas, dataset, provenance, helpers, and focused tests only. **Finish evidence:** focused tests pass or the unavailable test capability is recorded exactly.

### WU-04 — Implement subject aggregation, fidelity, and anatomy metrics (`T-16-04`)

**Depends on:** WU-03.  
**Production paths:** `src/pada3dacb/evaluation/concepts/{aggregation.py,fidelity.py,anatomy.py}`.  
**Test paths:** `tests/{test_concept_aggregation.py,test_concept_fidelity.py,test_concept_anatomy.py}`.

- [x] Add RED tests for source OOF uniqueness, target fold ensembles, fold-then-seed aggregation, per-seed retention, direction separation, and immutable `c_target`/`g_bar`. <!-- sdd-owner: implementation -->
- [x] Implement subject-level aggregation so repeated fold/seed outputs never become independent subjects and transfer directions are never pooled. <!-- sdd-owner: implementation -->
- [x] Implement global, per-subject, and per-ROI concept-fidelity MAE, RMSE, bias, Pearson, and Spearman metrics. <!-- sdd-owner: implementation -->
- [x] Implement anatomical consistency against `g_bar`, keeping unweighted descriptive metrics separate from the canonical weighted anatomy score. <!-- sdd-owner: implementation -->
- [x] Implement explicit correlation availability status and reasons `constant_roi`, `insufficient_samples`, and `numerical_error`; never substitute zero for unavailable correlations. <!-- sdd-owner: implementation -->
- [x] Triangulate against direct numerical references, singleton/constant ROIs, insufficient samples, weighted-score cases, and non-finite inputs; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_aggregation.py tests/test_concept_fidelity.py tests/test_concept_anatomy.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** aggregation, fidelity, anatomy, and focused tests only. **Finish evidence:** aggregation and metric reference assertions pass.

### WU-05 — Implement head agreement, ROI stability, and class profiles (`T-16-05`)

**Depends on:** WU-04.  
**Production paths:** `src/pada3dacb/evaluation/concepts/{agreement.py,stability.py,class_profiles.py}`.  
**Test paths:** `tests/{test_concept_agreement.py,test_concept_stability.py,test_concept_class_profiles.py}`.

- [x] Add RED tests for latent/concept predictive metrics, top-1 agreement/disagreement, JS divergence, consistency-loss direction, per-class disagreement counts, and separation from concept fidelity. <!-- sdd-owner: implementation -->
- [x] Implement head-agreement metrics with fixed class order and explicit probability handling. <!-- sdd-owner: implementation -->
- [x] Add RED tests for fold/seed ROI profiles, pairwise Spearman correlation, mean pairwise correlation, per-ROI standard deviation, configured top-k Jaccard, and rank dispersion. <!-- sdd-owner: implementation -->
- [x] Implement ROI stability using the terms `attention profile`, `concept profile`, and `ROI stability`; reject causal-importance, biomarker, disease-mechanism, and equivalent causal terminology in generated contracts. <!-- sdd-owner: implementation -->
- [x] Implement descriptive CN/MCI/AD concept, `c_target`, and `g_bar` profiles with class support and subject-level bootstrap hooks; do not add unrestricted ROI-by-ROI inference. <!-- sdd-owner: implementation -->
- [x] Triangulate with hand-computed JS/agreement values, one-instance stability behavior, top-k configuration validation, empty-class handling, and terminology assertions; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_agreement.py tests/test_concept_stability.py tests/test_concept_class_profiles.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** agreement, stability, class-profile, and focused tests only. **Finish evidence:** focused tests pass and terminology constraints are verified.

### WU-06 — Implement statistics, figures, and tables (`T-16-06`)

**Depends on:** WU-05.  
**Production paths:** `src/pada3dacb/evaluation/concepts/{statistics.py,figures.py,tables.py}`.  
**Test paths:** `tests/{test_concept_statistics.py,test_concept_figures.py,test_concept_tables.py}`.

- [x] Add RED tests proving reuse of Phase 15 subject-level stratified bootstrap with explicit seed, replicate accounting, no ROI/fold-level resampling, and deterministic results. <!-- sdd-owner: implementation -->
- [x] Implement paired subject comparisons for `prototype_pseudo` versus `source_only`, `coral`, `mmd`, and `cdan` across concept MAE, anatomy MAE, and JS divergence. <!-- sdd-owner: implementation -->
- [x] Implement Holm correction separately by direction, checkpoint policy, and metric family with exactly four PADA comparator slots; exclude AAGN/FasterSNN. <!-- sdd-owner: implementation -->
- [x] Generate all required machine-readable tables with ROI-indexed vectors and all required figures using fixed ROI order and predeclared top-k values, without favorable-ROI selection or intervention figures. <!-- sdd-owner: implementation -->
- [x] Triangulate bootstrap invalid/unavailable replicate accounting, paired-subject alignment, Holm reference results, complete output names, and deterministic figure/table fixtures; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_statistics.py tests/test_concept_figures.py tests/test_concept_tables.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** statistics, figures, tables, and focused tests only. **Finish evidence:** reference statistics and output-contract tests pass.

### WU-07 — Add independent mathematical verification (`T-16-07`)

**Depends on:** WU-06.  
**Test paths:** `tests/{test_concept_metrics_reference.py,test_concept_statistics_reference.py,test_concept_statistics_edge_cases.py}`.

- [x] Add independent reference tests for MAE/RMSE/bias/correlation equations, anatomy weighting, JS divergence, aggregation order, bootstrap unit, and Holm correction. <!-- sdd-owner: implementation -->
- [x] Add edge-case tests for constant ROIs, insufficient samples, numerical failures, unavailable metrics, missing class support, and paired-subject mismatches. <!-- sdd-owner: implementation -->
- [x] Verify that synthetic inference performs no target adaptation, gradient computation, parameter update, target-label use in adaptation, or artifact regeneration. <!-- sdd-owner: implementation -->
- [x] Run `python -m pytest tests/test_concept_metrics_reference.py tests/test_concept_statistics_reference.py tests/test_concept_statistics_edge_cases.py -q --basetemp=artifacts/pytest-tmp-phase16` and resolve any mathematical discrepancy before integration. <!-- sdd-owner: implementation -->

**Rollback:** independent reference tests only. **Finish evidence:** mathematical verification PASS.

### WU-08 — Implement report orchestration, CLI, configuration, and real-run gate (`T-16-08`)

**Depends on:** WU-07.  
**Production paths:** `src/pada3dacb/evaluation/concepts/report.py`, `scripts/evaluate_concepts.py`, `configs/evaluation/concepts.yaml`, `src/pada3dacb/evaluation/__init__.py`, `src/pada3dacb/config.py`, `src/pada3dacb/exceptions.py`, `pyproject.toml`.  
**Test path:** `tests/test_concept_cli.py`.

- [x] Add RED CLI tests for every required flag, CPU-default/device selection, direction selection, method selection, checkpoint policies, sensitivity, overwrite, dry-run, and validate-only behavior. <!-- sdd-owner: implementation -->
- [x] Implement report orchestration and atomic output tree creation for manifests, resolved config, provenance, method status, logs, subject outputs, tables, figures, and primary/sensitivity policies. <!-- sdd-owner: implementation -->
- [x] Implement the CLI so dry-run discovers and validates without forward passes or artifacts, while validate-only runs one no-grad batch without bootstrap, figures, or parameter updates. <!-- sdd-owner: implementation -->
- [x] Implement the real-run gate requiring authorization and explicit expected hashes; enumerate unresolved gates and fail closed when unauthorized or hashes are null/mismatched. <!-- sdd-owner: implementation -->
- [x] Configure fixed class order, explicit real-run top-k values, bootstrap defaults, expected folds/seeds, and `authorized: false` in `configs/evaluation/concepts.yaml`. <!-- sdd-owner: implementation -->
- [x] Triangulate CLI exit behavior, no-training import checks, no-artifact dry-run behavior, validate-only boundaries, reuse semantics, and manifest provenance; then refactor after focused tests pass. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** report, CLI, configuration, package exports, shared config/exception adjustments, and focused tests only. **Finish evidence:** CLI-focused tests pass.

### WU-09 — Complete integration and regression protection (`T-16-09`)

**Depends on:** WU-08.  
**Test paths:** `tests/{phase16_integration_fixtures.py,test_concept_integration.py,test_concept_modes.py,test_concept_boundaries.py,test_concept_regressions.py,test_all_methods_regression_phase16.py,test_proposed_method_cli.py}`.

- [x] Add deterministic synthetic fixtures covering both transfer directions, all folds/seeds, primary and sensitivity checkpoints, all eligible PADA methods, and AAGN/FasterSNN not-applicable statuses. <!-- sdd-owner: implementation -->
- [x] Add integration tests for complete dry-run, validate-only, full synthetic evaluation, reuse, manifest/provenance outputs, and required tables/figures. <!-- sdd-owner: implementation -->
- [x] Add boundary tests proving no training invocation, no target-adaptation loader, no target-label leakage, no concept/Jacobian recomputation, no subject reassignment, no causal terminology, and no Phase 17 paths. <!-- sdd-owner: implementation -->
- [x] Add regression tests for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, FasterSNN, and Phase 15 predictive evaluation behavior. <!-- sdd-owner: implementation -->
- [x] Verify with `python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16`. <!-- sdd-owner: implementation -->

**Rollback:** integration fixtures and regression tests only. **Finish evidence:** integration and regression suites pass.

### WU-10 — Document evaluator use and scientific limitations (`T-16-10`)

**Depends on:** WU-09.  
**Paths:** `docs/CONCEPT_EVALUATION.md`, `docs/PHASE16_REPORT.md`, `docs/IMPLEMENTATION_AUDIT.md`.

- [x] Document safe CLI usage, synthetic-only validation, configuration gates, tensor/output contracts, aggregation policy, metric equations, unavailable values, provenance, and deterministic output layout. <!-- sdd-owner: implementation -->
- [x] Record actual focused/full validation evidence, implementation scope, limitations, blocked manuscript scores, and the native receipt #1793 delivery restriction (resolved by the approved post-apply gate) without overstating scientific results. <!-- sdd-owner: implementation -->
- [x] Audit documentation for fixed class order, target-label firewall, no causal claims, no real-data authorization, and explicit confirmation that Phase 17 was not started. <!-- sdd-owner: implementation -->

**Rollback:** documentation only. **Finish evidence:** documentation matches implemented behavior and validation evidence.

### WU-11 — Perform final independent audit (`T-16-11`)

**Depends on:** WU-10.  
**Path:** `specs/phase_16_concept_validation/final_audit.md`.

- [x] Audit scientific equations, ROI/concept provenance, aggregation, target-label firewall, unavailable handling, previous-phase regressions, required outputs, and absence of Phase 17 work. <!-- sdd-owner: implementation -->
- [x] Record PASS, warnings, or blockers with file-path evidence; do not modify implementation while auditing. <!-- sdd-owner: implementation -->
- [x] Require remediation of every blocker before final validation and preserve the native receipt delivery restriction until the post-apply gate returned allow. <!-- sdd-owner: implementation -->

**Rollback:** final audit file only. **Finish evidence:** final audit PASS.

### WU-12 — Run final validation and synthetic lifecycle evidence (`T-16-12`)

**Depends on:** WU-11.  
**Paths:** no repository files owned; record results in the active phase report/Engram only.

- [x] Run `python -m pip install -e .` and `python -c "import pada3dacb; print(pada3dacb.__version__)"`; record exact exit codes and installation limitations. <!-- sdd-owner: implementation -->
- [x] Run the focused concept tests, integration/regression tests, full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16`, `python -m ruff check .`, and `git diff --check`; record exact results (the full-suite timeout is incomplete evidence, not a pass). <!-- sdd-owner: implementation -->
- [x] Run synthetic dry-run, validate-only, full evaluation, and reuse CLI commands from `specs/phase_16_concept_validation/acceptance.md`; verify no real ADNI/OASIS evaluation occurs. <!-- sdd-owner: implementation -->
- [x] Confirm no repository bytes are changed by validation, no delivery action bypasses the native receipt, and the next phase is not started. <!-- sdd-owner: implementation -->

**Rollback:** no repository bytes. **Finish evidence:** complete validation receipt in the phase report/active backend.

### WU-13 — Maintain OpenSpec planning mirrors (`T-16-13`)

**Depends on:** planning dependencies only; do not block synthetic implementation on administrative delivery.  
**Paths:** `openspec/changes/phase-16-concept-validation/{proposal.md,design.md,tasks.md}`, `openspec/changes/phase-16-concept-validation/specs/phase-16-concept-validation/spec.md`, and `specs/phase_16_concept_validation/agent_plan.yaml`.

- [x] Keep proposal, capability specification, design, tasks, and agent-plan mirrors synchronized with the approved Phase 16 scope, ownership, dependencies, forecast, and blockers. <!-- sdd-owner: implementation -->
- [x] Verify every task path has one owner, every work unit has a start/finish/verification/rollback boundary, and no task authorizes prohibited training or Phase 17 paths. <!-- sdd-owner: implementation -->
- [x] Record the native receipt #1793 restriction as an administrative delivery blocker that was lifted when the post-apply gate returned allow; branches, commits, and pull requests were held only until that resolution. <!-- sdd-owner: implementation -->

**Rollback:** OpenSpec mirrors and agent plan only. **Finish evidence:** exact planning and ownership evidence.

## Parent-owned post-apply actions

- [x] Start or reuse one bounded implementation review after apply, using the native receipt lifecycle and the review workload forecast; do not launch a second budget for a repeated gate. <!-- sdd-owner: parent -->
- [x] Validate the existing content-bound receipt at the required lifecycle gate and stop on any native receipt, provenance, or scope failure; the content-bound receipt was validated and the post-apply gate returned allow (incident #1793 resolved by the approved receipt). <!-- sdd-owner: parent -->
