# Phase 16: Concept Validation

## Intent

Implement the concept evaluation component of PADA-3DACB, providing quantitative concept, anatomical consistency, head agreement, and ROI stability evaluation for domain adaptation methods. This phase provides read‑only analysis of concept predictions (c_hat) against anatomical and clinical references, without modifying training or adaptation behavior.

## Problem Statement

The repository implements domain adaptation methods (Source‑Only, CORAL, MMD, CDAN, prototype_pseudo) but lacks a dedicated evaluation module for the quantitative concept‑level analysis required to assess anatomical consistency and prediction reliability. Phase 16 adds this evaluation capability while preserving the existing training/adaptation pipelines.

## Users and Review Context

| User or reviewer | Needed outcome |
|------------------|----------------|
| Repository maintainers | A self‑contained, testable concept evaluation package that integrates with the existing codebase. |
| Scientific investigators | Quantitative scores (MAE, RMSE, Pearson, etc.) for concept fidelity, anatomical consistency, head agreement, and ROI stability, stratified by diagnosis. |
| Statistical reviewers | Correct aggregation (subject‑level, fold‑then‑seed), confidence‑interval handling, and proper treatment of unavailable values. |
| Publication reviewers | Machine‑readable outputs, provenance tracking, and clearly separated primary/sensitivity results. |
| Reproducibility auditors | Exact input hashes, provenance records, and deterministic execution. |

## Proposed Outcome

Phase 16 will deliver:

1. A `pada3dacb.evaluation.concepts` package containing:
   - Dataset, discovery, provenance, inference modules.
   - Aggregation, fidelity, anatomy, agreement, stability components.
   - Statistics, figure, table, and report generators.
2. A command‑line script `scripts/evaluate_concepts.py` that executes the evaluation workflow.
3. A configuration file `configs/evaluation/concepts.yaml` controlling execution.
4. Comprehensive unit tests covering the new functionality.
5. Documentation specifying the tensor contracts, aggregation rules, and metric definitions.

The implementation will be strictly read‑only with respect to training/adaptation state; it will only read pre‑computed concept targets (`c_target`) and anatomical references (`g_bar`) and produce evaluation artifacts.

## Binding Scientific Rules

- **Fixed class order**: CN = 0, MCI = 1, AD = 2.
- **Concept fidelity**: Compare `c_hat` to immutable `c_target` using MAE, RMSE, bias, Pearson/Spearman with proper unavailable handling.
- **Anatomical consistency**: Compare `c_hat` to immutable `g_bar` (canonical anatomical reference) using the same statistical measures, reported both unweighted and canonical‑weighted.
- **Head agreement**: Evaluate diagnostic predictions derived from `c_hat` (via a lightweight head) against true labels, reporting accuracy, balanced accuracy, F1, etc., while preserving the distinction from concept fidelity.
- **ROI stability**: Compute pairwise Spearman correlations, Jaccard indices of top‑k ranks, and dispersion statistics across subjects.
- **Class‑conditional statistics**: Provide means and bootstrap confidence intervals for each diagnostic group.
- **Method comparisons**: Perform paired statistical tests (bootstrap, McNemar) with Holm correction across directions, checkpoints, and metric families.
- **Provenance**: Require input hashes (atlas, ROI‑order, concept normalizer) and reject candidates with missing or mismatched provenance.
- **Real‑run gate**: By default (`authorized: false`) the module refuses to process real ADNI/OASIS data; synthetic tests must pass before enabling real evaluation.
- **Target‑label firewall**: No target labels are used during adaptation; evaluation uses only source‑validation and target‑evaluation partitions.

## Scope

### In scope

- Definition of tensor contracts for `c_hat`, `c_target`, `g_bar`, `alpha`, logits, probabilities.
- Subject‑level aggregation (fold‑then‑seed, no pooling across directions).
- Computation of the fidelity, anatomy, agreement, and stability metric families.
- Generation of intermediate and final outputs (CSV, JSON, plots) as specified in `output_schema.md`.
- CLI with `--config`, `--runs-root`, `--output-root`, `--direction`, `--both-directions`, `--method`, `--all-methods`, `--checkpoint-policy`, `--include-sensitivity`, `--bootstrap-replicates`, `--bootstrap-seed`, `--overwrite`, `--dry-run`, `--validate-only`.
- Machine‑readable manifest (`evaluation_manifest.json`), config dump, provenance report, method status, computational summary, and log.
- Deterministic synthetic tests covering all methods, directions, and checkpoint policies.
- Documentation of all assumptions, equations, and implementation details.

### Out of scope and non‑goals

- Training or modification of adaptation model weights.
- Regeneration of concept targets, anatomical references, or Jacobians.
- Use of target labels in adaptation loops.
- Real evaluation of ADNI/OASIS data before the `authorized` flag is set to `true` (requires independent approval).
- Changes to existing Source‑Only, CORAL, MMD, CDAN, or prototype_pseudo training code.
- Introduction of new cohorts or external data.
- Any modifications to previously approved phases (12‑15).

## Dependencies and Preconditions

- Phase 15 (Predictive Evaluation) must be complete and its artifacts available, as the concept evaluator may reuse shared utilities (e.g., provenance hashing).
- All Phase 16 specific files must be created under the paths declared in the agent plan.
- The experiment harness must remain unchanged; the concept evaluator is invoked via its own CLI script.
- Prior to real‑data execution, the `authorized` flag in the configuration must be set to `true` only after explicit stakeholder approval.

## Unresolved Gates

### Scientific and publication gates

- Real evaluation remains blocked until the `authorized` flag is flipped to `true` via a separate approval process (outside this phase).
- Manuscript‑level scores (CFS, ACS, PCS, QIS) are marked as *BLOCKED* pending identification of verifiable equations in authoritative sources; the implementation provides transparent fallback metrics.

### Administrative delivery gate

- Native receipt issue #1793 remains unresolved; it does not block proposal authoring but blocks archive, commit, push, PR, release, and publication until native receipt authority is restored.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inadvertent use of target labels in adaptation | Violates scientific assumptions | Code review and static analysis to confirm absence of `diagnosis` or `diagnosis_label` in adaptation batches. |
| Incorrect aggregation (e.g., pooling directions) | Biased statistics | Unit tests that assert subject‑level separation and verify aggregate counts. |
| Missing provenance checks | Untraceable results | Integration tests that trigger exclusion when input hashes mismatch. |
| Failure to handle unavailable values | Silent substitution of zero or NaN | Specific tests for `UNAVAILABLE` status propagation. |

## Proposal Question Round

The proposal phase was completed as part of the SDD initialization; the content above reflects the agreed‑upon scope and bindings for Phase 16.

## Planning mirror and delivery boundary

The planning mirrors are the proposal, capability specification, design, task list, and repository agent plan. They must describe the same Phase 16 scope, ownership, dependency order, review forecast, and blockers.

- WU-13 owns only these planning artifacts: `openspec/changes/phase-16-concept-validation/{proposal.md,design.md,tasks.md}`, `openspec/changes/phase-16-concept-validation/specs/phase-16-concept-validation/spec.md`, and `specs/phase_16_concept_validation/agent_plan.yaml`.
- Planning maintenance is implementation-owned; parent-owned review, receipt validation, commit, push, PR, archive, and release actions remain deferred.
- Delivery planning is `auto-chain` with `feature-branch-chain`; each work-unit slice remains subject to the 400-authored-line ceiling and no size exception is authorized.
- Native receipt #1793 is an administrative delivery blocker only. It does not block planning maintenance or synthetic implementation/verification, but it forbids branch, commit, PR, archive, release, and publication actions while unresolved.
- WU-13 must not authorize training/adaptation changes, target-label use in adaptation, real-data evaluation, or Phase 17 production work.