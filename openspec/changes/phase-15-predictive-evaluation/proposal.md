# Phase 15: Publication-Grade Predictive Evaluation

## Intent

Establish a publication-grade, read-only predictive evaluation workflow over existing immutable subject-level prediction exports for Source-Only, CORAL, MMD, CDAN, prototype_pseudo, AAGN, and FasterSNN.

The workflow will give maintainers, scientific reviewers, statistical reviewers, and publication reviewers a reproducible way to determine which exports are admissible, how predictions are aggregated without pseudo-replication, and how methods are compared without using target outcomes for model or checkpoint selection. It will keep `ADNI -> OASIS` and `OASIS -> ADNI` as separate analyses and produce traceable machine-readable and publication-ready evaluation artifacts.

This proposal authorizes planning for Phase 15 only. It does not authorize real comparative evaluation or publication while required exports or scientific decisions remain unresolved.

## Problem Statement

The repository contains approved training and prediction-export behavior for seven methods, but it does not yet contain a functional Phase 15 evaluator. The existing `src/pada3dacb/evaluation/__init__.py` and `scripts/evaluate.py` are intentional fail-closed placeholders, not an implementation.

The prediction exports also come from two schema families and distribute identity and provenance differently. Without a controlled evaluation layer, maintainers would have to reconcile exports manually, risking:

- incompatible or incomplete runs entering comparisons;
- target outcomes influencing checkpoint or method selection;
- repeated fold, seed, or checkpoint predictions being treated as independent samples;
- silent replacement or concealment of undefined metrics and failed inputs;
- aggregation across transfer directions or inconsistent subject populations;
- tables and statistical claims that cannot be traced to immutable inputs.

Phase 15 addresses this scientific reproducibility and reviewability gap without changing training behavior or regenerating predictions.

## Users and Review Context

| User or reviewer | Needed outcome |
|---|---|
| Repository maintainers | A fail-closed way to discover, validate, include, or exclude immutable prediction exports. |
| Scientific investigators | Direction-specific metrics and comparisons that preserve the subject as the statistical unit. |
| Statistical reviewers | Auditable aggregation, uncertainty, paired-comparison, multiplicity, and undefined-result handling. |
| Publication reviewers | Traceable tables and confusion matrices with explicit primary and sensitivity analyses. |
| Reproducibility auditors | Input hashes, provenance checks, status reports, and deterministic output organization. |

## Proposed Outcome

Phase 15 will define and implement a read-only evaluation workflow that:

1. discovers configured prediction exports without altering them;
2. validates file hashes, provenance, schema compatibility, identity agreement, and completeness;
3. records every method's inclusion or exclusion with explicit reasons;
4. normalizes the approved export families into one subject-level evaluation contract;
5. aggregates folds and seeds in the predeclared order without pseudo-replication;
6. generates direction-isolated primary and sensitivity results;
7. reports metrics, per-class availability, confusion matrices, uncertainty, and paired comparisons;
8. emits machine-readable and publication-oriented tables with complete provenance; and
9. supports dry-run and validate-only CLI modes before any evaluation output is produced.

Exact formulas, confidence-interval policies, comparison-family construction, invalid-replicate rules, and detailed output schemas belong to the later `statistical_protocol.md` and Phase 15 specification/design artifacts. They must implement the binding decisions without inventing unresolved statistical policy in this proposal.

## Binding Scientific Rules

### Analysis boundaries

- Analyze `ADNI -> OASIS` and `OASIS -> ADNI` separately.
- Treat each direction as a separate analysis and hypothesis family.
- Use the subject as the statistical unit.
- Never treat repeated fold, seed, or checkpoint predictions as independent observations.

### Checkpoint policy

- Primary checkpoint: predeclared `best_source_f1`.
- Sensitivity checkpoint: `last`, reported separately.
- Target outcomes must never select checkpoints, methods, comparisons, hyperparameters, or reporting subsets.
- Repository checkpoint behavior remains authoritative pending resolution of D-14-002.

### Aggregation policy

- Source validation uses pooled out-of-fold predictions with each source subject appearing exactly once per direction, method, seed, and checkpoint.
- Target predictions require one prediction per subject per source fold.
- Target class probabilities are averaged across source-fold models within each seed.
- Per-seed subject predictions and metrics are retained as robustness diagnostics.
- Publication-level subject probabilities are then averaged across the predeclared seed ensemble.
- No fold-level or seed-level pseudo-replication is permitted.

### Missing and undefined results

- Incomplete or incompatible methods remain visible in inclusion and status reports.
- Such methods are excluded fail-closed from comparisons.
- Undefined metrics carry a value representation, availability status, and reason; they are never silently replaced with zero.

## Scope

### In scope

- Read-only discovery of the two approved prediction-export families.
- Input hashing and provenance validation.
- Cross-file identity and compatibility validation.
- Explicit inclusion, exclusion, completeness, and status reports.
- Read-only normalization of export schema differences.
- Direction-specific and checkpoint-specific evaluation trees.
- Primary `best_source_f1` outputs and separate `last` sensitivity outputs.
- Aggregate metrics and per-class metric availability/status.
- Count and normalized confusion matrices.
- Subject-stratified bootstrap confidence intervals.
- Paired McNemar comparisons.
- Paired bootstrap metric differences.
- Holm multiplicity correction within predeclared direction-specific families.
- Publication-level subject tables and retained per-seed diagnostics.
- Machine-readable outputs and publication-oriented tables.
- Dry-run and validate-only CLI behavior.
- Complete output provenance linking results to immutable input files and policies.

### Out of scope and non-goals

- Real numerical ADNI/OASIS evaluation or comparative claims during planning or before all gates are cleared.
- Training invocation or prediction regeneration.
- Any change to models, losses, schedules, checkpoints, splits, preprocessing, artifacts, experiment configurations, or existing prediction exports.
- Any use of target outcomes for selection or tuning.
- Concept evaluation, interventions, ROI deletion, or attention-stability analysis.
- Manuscript generation or publication submission.
- New cohorts, methods, or external data.
- Retrospective alteration of Phase 14 scientific behavior.
- Phase 16 specification or production work.
- Premature selection of exact statistical formulas or policies not already binding.

## Affected Areas

Expected later Phase 15 work may affect only the evaluation and planning surfaces required to realize this proposal:

- the `pada3dacb.evaluation` package;
- the fail-closed `scripts/evaluate.py` boundary, when replaced under an approved specification;
- Phase 15 specifications, statistical protocol, tests, and evaluation documentation;
- generated evaluation outputs under the repository's approved results/output locations.

Training, adaptation, baseline, preprocessing, split, checkpoint, configuration, and immutable export-producing code are dependencies to validate, not areas to modify.

## Dependencies and Preconditions

- Phase 14 final audit and final validation are PASS and provide closure evidence for the seven approved methods.
- Complete authorized exports must be supplied for every method intended for a real comparison.
- Input-family normalization must preserve immutable files and verify identity across prediction rows, run manifests, and fold results.
- The later Phase 15 statistical protocol must receive independent statistical review before implementation.
- All required Phase 15 SDD artifacts, action dependencies, and exclusive file ownership must be complete before implementation.

## Unresolved Gates

### Scientific and publication gates

Real comparative evaluation and publication remain blocked until maintainers resolve and document:

- **D-14-001 — Prototype-loss weight:** repository `lambda_proto = 1.0` versus manuscript `lambda_proto = 0.2`.
- **D-14-002 — Checkpoint tie-breaking:** repository source-validation macro-F1 only versus manuscript mention of a macro-AUC tie-break.
- Availability and authorization of complete, compatible immutable prediction exports for the intended comparison set.
- Independent approval of the Phase 15 statistical protocol, including aggregation, metrics, confidence intervals, paired tests, Holm families, missing-class behavior, invalid replicates, schemas, and provenance.

Until these gates clear, Phase 15 may support planning, implementation with synthetic fixtures, dry-run, and validate-only behavior, but it must not produce or publish real comparative findings.

### Administrative delivery gate

Native receipt issue #1793 remains unresolved. It does not block proposal authoring, but it blocks archive, commit, push, PR, release, and publication until native receipt authority is restored and validated.

## Risks and Mitigations

| Risk | Impact | Mitigation required by later artifacts |
|---|---|---|
| Pseudo-replication across folds or seeds | Invalid uncertainty and overstated evidence | Enforce subject-level uniqueness and the binding fold-then-seed aggregation order. |
| Target leakage into selection | Biased comparisons and invalid publication claims | Predeclare primary/sensitivity checkpoints and prohibit target-driven selection everywhere. |
| Cross-direction mixing | Scientifically incoherent estimates and hypothesis families | Isolate discovery, aggregation, outputs, comparisons, and multiplicity by direction. |
| Incomplete or incompatible exports | Misleading rankings or hidden missingness | Fail closed while keeping excluded methods visible with reasons. |
| Provenance mismatch across files | Results attributed to the wrong run, split, method, or checkpoint | Hash inputs and require cross-file identity agreement before inclusion. |
| Undefined classes or invalid bootstrap replicates | Silent metric distortion | Represent availability and reasons explicitly; define exact policies in the reviewed statistical protocol. |
| Prematurely fixed statistical details | Overbuilt or scientifically unsupported implementation | Defer non-binding formulas and thresholds to `statistical_protocol.md` and independent review. |
| Manuscript/repository discrepancies | Results that cannot support defensible claims | Block real comparison and publication until D-14-001 and D-14-002 are resolved. |
| Accidental mutation of scientific behavior | Regression of approved methods | Keep evaluation read-only and prohibit changes to training, exports, configs, splits, and checkpoints. |
| Administrative receipt failure | Unreviewed delivery or publication | Keep archive and delivery operations blocked by issue #1793 until native validation succeeds. |

## Rollback and Failure Safety

Phase 15 must be additive and read-only with respect to scientific inputs. If evaluation behavior is later found invalid:

- discard generated Phase 15 output trees;
- disable or remove the Phase 15 evaluator and restore the existing fail-closed CLI boundary;
- retain immutable prediction exports and all Phase 14 behavior unchanged;
- invalidate affected evaluation claims and regenerate outputs only after protocol correction and approval.

No rollback may rewrite prediction exports, retrain models, alter checkpoints, or reinterpret unresolved discrepancies silently.

## Success Criteria

The Phase 15 proposal is successful when later approved work can demonstrate all of the following without violating the unresolved gates:

- Every candidate input is deterministically discovered, hashed, provenance-checked, and reported as included or excluded with a reason.
- Both approved export families are normalized read-only under one explicit subject-level contract.
- Source pooled OOF uniqueness is enforced exactly once per subject for the applicable identity tuple.
- Target probabilities follow the binding within-seed fold ensemble and predeclared across-seed ensemble order.
- Directions, primary outputs, and sensitivity outputs remain separate.
- Metrics and per-class results expose availability and reasons for undefined values.
- Count and normalized confusion matrices are generated from the correct publication-level subject predictions.
- Subject-stratified bootstrap intervals, paired McNemar tests, paired bootstrap differences, and Holm-adjusted results are produced only under the independently approved statistical protocol.
- Paired analyses verify compatible subject sets and exclude invalid comparisons fail-closed.
- Machine-readable and publication-oriented tables are traceable to immutable inputs and policy metadata.
- Dry-run and validate-only CLI modes can inspect planned work and admissibility without producing real comparative claims.
- Synthetic and validation evidence can exercise the workflow without requiring private ADNI/OASIS data.
- No target outcome affects selection, no approved training behavior changes, no real result is claimed before authorization, and Phase 16 is not started.

## Proposal Question Round

The interactive proposal gate was completed by the parent orchestration. The selected framing was **Use the supplied protocol**, so this proposal treats the provided preflight ledger, binding scientific decisions, scope boundaries, discrepancies, and publication gates as authoritative. Remaining exact statistical policy is intentionally deferred to the independently reviewed Phase 15 statistical protocol rather than inferred here.
