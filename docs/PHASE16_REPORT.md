# Phase 16 is technically implemented for deterministic synthetic evaluation

Phase 16 now implements the approved transparent concept, anatomical, agreement, ROI-stability, class-profile, statistical, reporting, and CLI contracts. Real cohort evaluation and publication results are intentionally absent.

## Outcome

| Boundary | Status |
|---|---|
| Production metric and data contracts | Implemented |
| Deterministic synthetic lifecycle | Implemented |
| Full method/direction/checkpoint fixture matrix | Implemented |
| Real ADNI/OASIS evaluation | Not run; CLI remains closed |
| CFS/ACS/PCS/QIS | Blocked; equations unavailable |
| Phase 17 | Not started |
| Archive/commit/push/PR/release/publication | Blocked by native incident #1793 |

## Implementation map

| Area | Files |
|---|---|
| Contracts and read-only data | `evaluation/concepts/schemas.py`, `dataset.py` |
| Discovery and provenance | `discovery.py`, `provenance.py` |
| No-grad inference | `inference.py` |
| Aggregation and metrics | `aggregation.py`, `fidelity.py`, `anatomy.py`, `agreement.py` |
| Stability and profiles | `stability.py`, `class_profiles.py` |
| Statistical inference | `statistics.py` |
| Tables, figures, output transaction | `tables.py`, `figures.py`, `report.py` |
| CLI and configuration | `scripts/evaluate_concepts.py`, `configs/evaluation/concepts.yaml` |

## Remediation after independent verification

The first independent static verification correctly rejected the initial implementation. Passing tests had hidden incomplete production paths. The remediation addressed each critical category:

1. Inference now consumes immutable precomputed `c_target` and `g_bar`; placeholder targets and hashes were removed.
2. Subject records now validate labels, domains, probabilities, argmax predictions, attention, dimensions, counters, and SHA-256 metadata.
3. Candidate issues are retained for provenance reporting and block inference.
4. Artifact hashing fails closed on missing normalizers, ROI order, checkpoints, target artifacts, or inconsistent hashes.
5. Bootstrap is diagnosis-stratified by subject; concept Holm families contain exactly four valid PADA-3DACB comparators.
6. ROI Jaccard and rank dispersion remain profile/statistic-specific instead of being averaged or discarded.
7. `L_cons` direction must be supplied explicitly from configuration.
8. Synthetic evaluation exercises fidelity, anatomy, agreement, stability, bootstrap, and paired-inference kernels.
9. The synthetic report now emits the complete output tree, 11 required tables, and five real PNG figures per direction/policy.
10. Real dry-run performs discovery; real validate/evaluate remain authorization-gated and closed.

## Scientific interpretation

Phase 16 outputs are descriptive and diagnostic. They do not establish causal importance, biomarkers, disease mechanisms, or publication performance. The fixed class order remains `(CN, MCI, AD) = (0, 1, 2)`. Target evaluation labels remain posthoc-only.

Method-comparison differences use the fixed orientation `prototype_pseudo - comparator` for each subject's own concept error, anatomy error, or within-method head JS divergence. AAGN and FasterSNN are reported as not applicable because they lack the PADA-3DACB concept head.

## Verification evidence

The final evidence table is maintained in `specs/phase_16_concept_validation/final_audit.md`. It records focused reference tests, the complete concept suite, previous-method regressions, the full repository suite, Ruff, diff validation, synthetic lifecycle byte identity, read-only reuse, and the closed real gate.

## Delivery boundary

This report does not archive or publish the phase. Native review/receipt incident #1793 remains a hard administrative blocker for archive, commit, push, PR, release, and publication. Resolving that incident must not change Phase 16 scientific behavior or silently begin Phase 17.
