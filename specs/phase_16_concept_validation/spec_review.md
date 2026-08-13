# Phase 16 Independent Scientific Specification Review

## Final verdict: PASS

The Phase 16 contract is approved for implementation. The review found no unresolved blocker in the scientific scope, aggregation rules, provenance gates, terminology constraints, or unavailable-state handling. The implementation gate remains downstream: production work must not begin unless this file remains `PASS`.

## Review scope and evidence

Reviewed the reconciled contract in:

- `specs/phase_16_concept_validation/requirements.md`
- `specs/phase_16_concept_validation/design.md`
- `specs/phase_16_concept_validation/tasks.md`
- `specs/phase_16_concept_validation/acceptance.md`
- `specs/phase_16_concept_validation/metric_protocol.md`
- `specs/phase_16_concept_validation/output_schema.md`
- `specs/phase_16_concept_validation/manuscript_extraction.md`
- `specs/phase_16_concept_validation/decisions.md`
- `specs/phase_16_concept_validation/agent_plan.yaml`

The plan records 14 actions, 66 owned paths, zero duplicate owned paths, and no size exception. This review is contract-level; it does not claim that downstream implementation or test work is complete.

## Scientific review findings

### 1. Manuscript score definitions — PASS with intentional blocked dispositions

CFS, ACS, PCS, and QIS have no complete, verifiable equations in the authoritative sources recorded by `manuscript_extraction.md`. The contract correctly marks each score `BLOCKED` and forbids deriving an equation from its name. Transparent fallback metrics are explicitly defined instead:

- CFS: concept fidelity MAE, RMSE, bias, Pearson, and Spearman.
- ACS: unweighted descriptive anatomy metrics plus a separately reported canonical weighted score when weights are available.
- PCS: head predictive metrics, top-1 agreement, JS divergence, and consistency direction.
- QIS: no invented replacement score; descriptive metrics remain available.

This is an intentional scientific gate, not an unresolved implementation blocker.

### 2. Target-label isolation — PASS

The contract separates `source_validation` and `target_evaluation` partitions, forbids target adaptation, training imports, gradients, parameter updates, normalizer refitting, concept/Jacobian recomputation, and subject reassignment. True labels may support post-hoc descriptive head/agreement summaries, but must not enter adaptation, method selection, checkpoint selection, or target training behavior.

### 3. Subject and direction aggregation — PASS

The required order is explicit and internally consistent:

1. Source validation uses true out-of-fold records, with each source subject represented once per method and seed.
2. Target evaluation averages fold predictions into one subject-level ensemble while preserving immutable `c_target` and `g_bar`.
3. Multiple seeds aggregate only after fold aggregation and retain per-seed records.
4. Transfer directions remain separate.

Repeated fold or seed outputs are not independent subjects, and bootstrap resampling occurs only after subject-level aggregation.

### 4. Causal and interpretive overclaiming — PASS

The contract forbids causal claims, interventions, ROI deletion/retraining, architecture ablations, and Phase 17 work. It requires the descriptive terms `attention profile`, `concept profile`, and `ROI stability`, and rejects causal-importance, biomarker, disease-mechanism, and equivalent terminology. Agreement with `g_bar` is explicitly not treated as proof of causal or pathological validity.

### 5. Unavailable-state handling — PASS

Undefined metrics are represented explicitly rather than converted to zero or silently dropped:

- Correlations: `UNAVAILABLE` with `constant_roi`, `insufficient_samples`, or `numerical_error`.
- Weighted anatomy: `UNAVAILABLE` with `weights_unavailable` when canonical weights are absent.
- Empty class/group cases: explicit unavailable status and reason.
- Bootstrap accounting separately tracks requested, successful, invalid, and unavailable results.

### 6. Method applicability — PASS

AAGN and FasterSNN are explicitly reported as `not_applicable_no_pada3dacb_concept_head`; they are not treated as failed methods and are excluded from PADA concept comparisons.

### 7. Provenance and real-run authorization — PASS

The contract requires the declared provenance fields, exact input hashes, fixed class order `CN=0, MCI=1, AD=2`, canonical ROI order, and concept-normalizer compatibility. Real evaluation remains fail-closed because `authorized: false` is the default and required expected hashes/approval gates must be explicitly resolved. Synthetic validation is distinguished from real evaluation.

## Blocking findings

**None.** The blocked manuscript-score dispositions and the unauthorized real-run state are deliberate scientific safeguards and are documented as such; neither authorizes invented equations or real-data execution.

## Implementation gate

Implementation may begin with WU-03 / `T-16-03` only after this review remains `PASS`. No production implementation is authorized by this review itself, and this work unit does not modify training, adaptation, data, model, loss, experiment, artifact, or Phase 17 paths.
