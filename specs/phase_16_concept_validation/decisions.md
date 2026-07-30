# Phase 16 — Decisions

## D-16-01: A-A-GAN vs AAGN naming
**Decision**: Use `AAGN` consistently throughout Phase 16.
**Rationale**: The canonical registry ID is `aagn` with display name `AAGN / ROI-aware gating`. The hyphenated form `A-A-GAN` appears only in legacy Phase 15 docs and is corrected.
**Scope**: All Phase 16 code, docs, configs, schemas.
**Status**: Applied in AGENTS.md, docs/IMPLEMENTATION_AUDIT.md, docs/PHASE15_REPORT.md, docs/PREDICTIVE_EVALUATION.md.

## D-16-02: CFS/ACS/PCS/QIS manuscript scores
**Decision**: Mark all four scores as BLOCKED until verified from authoritative sources.
**Rationale**: Search of `notebooks/archive/training_original.ipynb`, `notebooks/archive/precompute_original.ipynb`, `docs/PROPOSED_METHOD_EXPERIMENT.md` yields no complete equations for these named scores. Cannot invent from names alone.
**Action**: Implement transparent metrics (MAE, RMSE, bias, correlations, JS divergence) as specified in requirements. If manuscript equations are later verified, add as supplementary.
**Status**: BLOCKED.

## D-16-03: Concept-normalizer hash provenance
**Decision**: Require explicit `concept_normalizer.expected_hash` in config for real runs; synthetic fixtures provide known hash.
**Rationale**: Prevents evaluating outputs from incompatible normalizers. Hash must be SHA-256 of normalizer JSON.
**Scope**: `configs/evaluation/concepts.yaml`, provenance validation.

## D-16-04: Atlas ROI-order hash
**Decision**: Require explicit `atlas.expected_roi_order_hash` in config.
**Rationale**: Ensures K and ROI ordering match between model, artifacts, and evaluation. Hash is SHA-256 of canonical ROI label sequence.
**Scope**: `configs/evaluation/concepts.yaml`, provenance validation.

## D-16-05: Target-adaptation exclusion
**Decision**: Strictly forbid target-adaptation loader, trainer imports, gradients, parameter updates, normalizer refitting, concept/Jacobian recomputation, subject reassignment.
**Rationale**: Phase 16 is posthoc evaluation only. Any violation is a phase boundary breach.
**Enforcement**: Static analysis in tests; runtime checks in discovery/inference.

## D-16-06: AAGN/FasterSNN not-applicable status
**Decision**: Report as `not_applicable_no_pada3dacb_concept_head` in method_status.csv and provenance. Do not treat as failed/incomplete.
**Rationale**: These baselines lack PADA-3DACB concept heads. Evaluation must not conflate absence with failure.
**Implementation**: `discovery.py` filters to PADA methods; `schemas.py` has explicit `NOT_APPLICABLE` status enum.

## D-16-07: Bootstrap unit
**Decision**: Subject-level only. Do not bootstrap ROI entries or repeated fold outputs.
**Rationale**: ROI entries are not independent subjects. Fold outputs are not independent before subject aggregation.
**Enforcement**: `statistics.py` uses Phase 15 subject bootstrap infrastructure exclusively.

## D-16-08: Correlation unavailable handling
**Decision**: Return explicit `UNAVAILABLE` status with reason (`constant_roi`, `insufficient_samples`, `numerical_error`). Never replace with zero.
**Rationale**: Zero correlation is a valid result; unavailable is not. Conflation would bias aggregate metrics.
**Implementation**: `fidelity.py` and `anatomy.py` correlation functions return `CorrelationResult` with status/reason.

## D-16-09: Weighted vs unweighted anatomy score
**Decision**: Report both separately. Unweighted descriptive = uniform weights. Canonical weighted = uses anatomical loss ROI weights (if available).
**Rationale**: Prevents conflation of descriptive agreement with canonical loss evaluation.
**Scope**: `anatomy.py` computes both; `tables.py` outputs separate tables/columns.

## D-16-10: Real-run gate defaults
**Decision**: `authorized: false` by default in `concepts.yaml`. Real runs fail unless all four gate hashes are explicitly resolved.
**Rationale**: Safety gate consistent with Phase 15. Prevents accidental real evaluation.
**Scope**: `configs/evaluation/concepts.yaml`, CLI real-gate check.

## D-16-11: Top-k configuration
**Decision**: Real-run top-k values explicit in config (`top_k: [5, 10, 20]`). Synthetic fixtures use small test-only values.
**Rationale**: Prevents implicit cherry-picking. Configuration drives figure/table generation.

## D-16-12: Causal terminology prohibition
**Decision**: Schemas, tables, figures, docs must not use: `causal importance`, `biomarker`, `disease mechanism`, `causal`, `mechanistic`. Use: `attention profile`, `concept profile`, `ROI stability`, `descriptive`, `observational`.
**Rationale**: Phase 16 is posthoc descriptive evaluation. Causal claims require separate approved phase.
**Enforcement**: Schema validation, doc review, test assertions.

## D-16-13: Device selection
**Decision**: `--device` CLI flag with default `cpu`. `cuda` optional. No automatic GPU detection.
**Rationale**: Explicit control for CI and synthetic runs. GPU tests remain optional.

## D-16-14: Phase 15 utility reuse
**Decision**: Reuse Phase 15 deterministic PCG64 stratified-resampling primitives and shared enums. Keep concept-specific result schemas and Holm assembly because Phase 15 hard-codes a six-comparator predictive family while FR-09 requires four PADA-3DACB comparators.
**Rationale**: Preserve the approved sampling protocol without admitting AAGN or FasterSNN into concept inference.
**Scope**: Concept statistics import the Phase 15 stratified index-draw primitive; comparator/result contracts remain Phase 16-specific.

## D-16-15: Output format for vectors
**Decision**: ROI-indexed columns (`roi_0`, `roi_1`, ..., `roi_{K-1}`) in CSV/Parquet plus metadata columns. Do not flatten all K into human-facing summary tables unless explicitly required.
**Rationale**: Efficient machine-readable format. Human tables use aggregation.
**Scope**: `tables.py` subject outputs, fidelity/anatomy per-ROI tables.

## D-16-16: WU-R25 disposition
**Decision**: WU-R25 satisfies T-15-16 (final-validation). No repository bytes modified; verification passes.
**Recorded**: Engram decision `decision/wu-r25-satisfies-t-15-16-disposition`.

## D-16-17: Native receipt #1793
**Decision**: Preserve as administrative delivery blocker only. Does not block synthetic implementation or verification.
**Scope**: Archive, commit, push, PR, release, publication blocked. Planning, synthetic impl, synthetic verification allowed.

## D-16-18: Manuscript score fallback
**Decision**: If CFS/ACS/PCS/QIS remain BLOCKED after manuscript extraction, continue with transparent metrics only. Do not invent equations.
**Rationale**: Scientific integrity. Transparent metrics (MAE, RMSE, bias, correlations, JS) are well-defined and sufficient for descriptive evaluation.
**Scope**: `metric_protocol.md` documents fallback.

## D-16-19: Class-conditional inference
**Decision**: Descriptive profiles only by default. Inferential class comparisons require separate predeclaration, multiplicity correction, independent approval.
**Rationale**: Avoids p-hacking. Phase 16 is descriptive; inference requires explicit protocol.

## D-16-20: Method comparison Holm families
**Decision**: Separate by direction, checkpoint policy, metric family (concept MAE, anatomy MAE, JS divergence). Each family contains exactly four comparisons: prototype_pseudo versus source_only, CORAL, MMD, and CDAN.
**Rationale**: FR-09 explicitly excludes AAGN and FasterSNN from concept comparisons. Holm correction still controls family-wise error within each predeclared four-comparator family.