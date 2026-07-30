# Phase 15 Decisions and Preflight Ledger

## Authorization

Phase 15 — Publication-Grade Predictive Evaluation, Confusion Matrices and Paired Statistical Comparison — was explicitly authorized by the user in the current orchestration session after Phase 14 final audit and final validation passed.

Authorization permits specification and implementation of read-only evaluation over existing immutable prediction exports. It does not authorize real ADNI/OASIS evaluation, publication claims, model training, scientific training changes, concept evaluation, manuscript generation, Phase 16 production work, commit, push, PR, or release.

## Phase 14 closure evidence

- Independent implementation final audit: PASS (`specs/phase_14_baselines/final_audit.md`; Engram observation 129).
- Final validation: PASS (`specs/phase_14_baselines/final_validation.md`; Engram observation 120).
- Fresh pre-Phase-15 baseline: `549 passed, 7 warnings in 249.12s`; Ruff passed; `git diff --check` passed.
- Approved and regression-protected methods: Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, and FasterSNN.
- The native review/receipt incident remains administrative and unresolved; upstream issue: https://github.com/Gentleman-Programming/gentle-ai/issues/1793.
- Native receipt resolution remains mandatory before archive, commit, push, PR, release, or publication.

## Pre-authorization Phase 15 boundary

No functional Phase 15 evaluator existed before authorization.

Two fail-closed boundary placeholders existed intentionally:

- `src/pada3dacb/evaluation/__init__.py`: namespace docstring only.
- `scripts/evaluate.py`: raises `PhaseNotImplementedError`.

No metrics, aggregation, provenance, confusion-matrix, bootstrap, paired-statistics, concept-evaluation, or Phase 16 production module existed. Phase 14 regression tests explicitly protected this boundary.

## Existing prediction-export families

Phase 15 must normalize two immutable input families without modifying training code:

1. Source-Only/CORAL/MMD/CDAN/prototype_pseudo: per-split, per-checkpoint CSV exports with the shared 18-column schema and identity fields in rows plus run manifests.
2. AAGN/FasterSNN: one combined `predictions.csv` per fold, with baseline identity and fold provenance distributed across `run_manifest.json` and `fold_result.json`.

No committed real or synthetic run output is available. Real evaluation therefore remains blocked until maintainers provide complete authorized exports and resolve the manuscript experiment configuration.

Discovery must compute input-file hashes, normalize schema differences read-only, require cross-file identity agreement, and reject incomplete or incompatible methods explicitly. No training-module change is currently justified.

## Binding scientific decisions

### Statistical unit

The subject is the statistical unit. Repeated predictions across folds, seeds, or checkpoints are never independent observations.

### Direction isolation

`ADNI -> OASIS` and `OASIS -> ADNI` remain separate analyses and hypothesis families.

### Checkpoint policies

- Primary: `best_source_f1`.
- Predeclared sensitivity: `last`.
- Target outcomes never choose checkpoints, methods, comparisons, or hyperparameters.

### Aggregation order

1. Validate one target prediction per subject per source fold.
2. Average class probabilities across source-fold models within each seed.
3. Calculate per-seed subject-level predictions and metrics.
4. Average predeclared per-seed subject probabilities for the publication-level subject table.
5. Retain per-seed metrics as robustness diagnostics.

Source-validation predictions use pooled out-of-fold uniqueness: one source subject exactly once per direction, method, seed, and checkpoint.

### Missing and undefined behavior

Incomplete methods remain visible in inclusion and status reports and are excluded fail-closed from comparisons. Undefined metrics are represented by value, availability status, and reason; they are never silently replaced by zero.

## Unresolved publication discrepancies

### D-14-001 — Prototype-loss weight

- Repository: `lambda_proto = 1.0`.
- Manuscript: `lambda_proto = 0.2`.
- Status: unresolved.
- Phase 15 rule: repository behavior is authoritative for engineering; do not execute or publish real comparative results until maintainers explicitly select and document the manuscript experiment configuration.

### D-14-002 — Checkpoint tie-breaking

- Repository: source-validation macro-F1 only.
- Manuscript: mentions macro-AUC tie-breaking.
- Status: unresolved.
- Phase 15 rule: repository checkpoint selection is authoritative; no target metric or retrospective evaluation result may alter it. Real comparative publication remains blocked pending maintainer resolution.

## Statistical protocol gate

Implementation is forbidden until all required Phase 15 SDD artifacts exist, file ownership has zero collisions, and an independent statistical reviewer approves:

- statistical unit and fold/seed aggregation;
- primary and sensitivity checkpoint policies;
- metric and per-class definitions;
- subject-level stratified bootstrap confidence intervals;
- paired McNemar and paired bootstrap comparisons;
- Holm family construction;
- missing-class and invalid-replicate behavior;
- complete output schemas and provenance requirements.

## Phase boundary

Concept validation, interventions, ROI deletion, attention stability, manuscript generation, real training, real evaluation, and Phase 16 production work remain prohibited.
