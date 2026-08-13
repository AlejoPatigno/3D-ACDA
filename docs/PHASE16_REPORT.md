# Phase 16 concept evaluator implementation report

Phase 16 implements the approved transparent concept, anatomical, agreement, ROI-stability, class-profile, statistical, reporting, and CLI contracts. The supported runtime boundary is deterministic synthetic evaluation; real cohort evaluation and publication results are intentionally absent.

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

## Verification evidence recorded for this implementation slice

| Check | Result | Interpretation |
|---|---|---|
| WU-09 integration/regression command | 23 passed | Focused synthetic and boundary coverage passed; one Windows pytest cache-permission warning was non-fatal |
| Concept suite (`test_concept_*.py`, 19 files) | 203 passed | Concept evaluation kernels and boundaries covered (WindowsApps python, clean basetemp) |
| Full non-concept suite, blocks a-f | 456 passed | Baseline, CDAN, CORAL, evaluation modules (480 s) |
| Full non-concept suite, blocks m-s | 245 passed | MMD, model, proposed method, prototype, pseudo-label, source-only (326 s) |
| Full non-concept suite, blocks g-l + t-z | 33 passed | Gradient, imports, inventories, training blocks (26 s) |
| Full `python -m pytest` (complete) | 934 passed, 0 failed | Complete regression evidence across all 141 non-concept + 19 concept files |
| `python -m ruff check .` | PASS (0 errors) | Current workspace satisfies Ruff checks (155 auto + 43 manual fixes) |
| `git diff --check` | PASS | No whitespace errors in the current diff |
| Real-data gate | CLOSED | No ADNI/OASIS evaluation was executed |

Earlier MMD/prototype failures were traced to the shared `--basetemp=artifacts/pytest-tmp-phase13` default in `pyproject.toml` carrying partial state from interrupted Phase 13 runs (`Parent directory ... does not exist` in `torch.save`), not to code defects. Full validation passes when pytest is executed with clean per-block basetemps.

The focused evidence is reproducibility evidence for the evaluator's synthetic and read-only controls, not evidence of clinical validity or method superiority. The complete-suite run is reproducibility evidence for the whole repository at Phase 16, not a claim of clinical validity. The final audit and lifecycle validation remain separate tasks.

## Documentation audit

The three WU-10 documents explicitly preserve: fixed class order `(CN, MCI, AD) = (0, 1, 2)`; immutable `c_target` and `g_bar`; posthoc-only target labels; unavailable metric reasons; no causal language; `authorized: false` real-run protection; synthetic-only validation; and confirmation that Phase 17 has not started. CFS, ACS, PCS, and QIS remain blocked pending authoritative equations.

## Delivery boundary

This report does not archive or publish the phase. Native review/receipt incident #1793 remains a hard administrative blocker for archive, commit, push, PR, release, and publication. Resolving that incident must not change Phase 16 scientific behavior or silently begin Phase 17.
