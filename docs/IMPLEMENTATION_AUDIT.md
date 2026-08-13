# Phase 15 Implementation Audit

## Scope

This audit describes implemented Phase 15 predictive evaluation behavior. The independent final audit required by T-15-15 returned **PASS** after remediation of C-01 through C-05. This document records the final implemented boundary.

## Implemented boundary

Phase 15 added a read-only evaluation package, safe CLI/configuration, exact output schemas, deterministic statistics, and CPU-only synthetic tests. It supports only:

- cohorts ADNI and OASIS;
- directions ADNIâ†’OASIS and OASISâ†’ADNI;
- methods Source-Only, CORAL, MMD, CDAN, PADA-3DACB, AAGN, and Faster-SNN;
- primary source-selected best checkpoint and separate last-checkpoint sensitivity;
- fixed labels `(CN,MCI,AD)=(0,1,2)`.

No training, optimizer, scheduler, checkpoint production, split generation, target-guided selection, concept evaluation, manuscript generation, or Phase 16 implementation was added.

## Architecture

`src/pada3dacb/evaluation/` separates immutable schemas, candidate discovery, provenance reconciliation, adapter normalization, aggregation, metrics, confusion matrices, bootstrap, paired statistics, multiple testing, table/figure projection, and report/output/reuse orchestration. `scripts/evaluate.py` owns parsing and safe dispatch; `configs/evaluation/predictive.yaml` owns explicit scientific configuration and the closed real gate.

Inputs are normalized into one canonical subject representation. All downstream statistics and publication projections derive from that table. This prevents cached fold summaries or incompatible populations from becoming alternative sources of truth.

## Scientific controls

- Subject, not fold, is the statistical unit.
- Target ensembles use complete fold-then-seed averaging.
- Source rows remain OOF and unique.
- Checkpoint policies and transfer directions remain separate.
- Target diagnosis labels do not enter adaptation training or checkpoint selection.
- Undefined metrics/inference remain null with explicit reasons.
- Paired analyses require identical ordered subjects and labels; no intersection fallback exists.
- Exact McNemar and predeclared paired-bootstrap families compare PADA-3DACB only with six comparators.
- Holm correction retains six slots even when hypotheses are unavailable.

## Provenance, privacy, and output controls

Every included candidate must prove exact provenance and file hashes. Canonical/public rows use only approved supplied subject hashes; raw identifiers are prohibited. Evaluation identity binds configuration, protocol/schema, library versions, authorization, and ordered inputs.

Output uses an exact allowlist, same-filesystem staging, manifest-last publication, guarded overwrite, previous-tree restoration, and read-only completed reuse. Dry-run and validate-only do not create output paths. Missing computational observations are null, never fabricated as zero.

## Verification traceability

Acceptance coverage is organized as follows:

- AC-15-001..017: discovery, adapters, provenance, privacy, aggregation, direction/policy isolation.
- AC-15-018..035: metric references, edge cases, confusion, bootstrap, pairing, McNemar, and Holm.
- AC-15-036..041: exact tree, projections, computational extraction, atomic writes, overwrite, and input immutability.
- AC-15-042..046: completed reuse, parser/modes, non-writing inspection, and closed real gate.
- AC-15-047..048: no training invocation and no prohibited/later-phase behavior.

**All AC-15-001 through AC-15-048 are PASS.** The final T-15-15 independent audit confirms complete requirements/acceptance traceability, ownership, scope, evidence, and administrative separation.

## Authorized correction during validation

Two Phase 14 regression guards encoded the historical rule that the Phase 15 confusion module must not exist. Once Phase 15 was explicitly authorized, those assertions became stale. With explicit maintainer approval, ownership was expanded only to remove the obsolete `confusion_matrices.py` prohibition. Remaining future-method and experiment-module prohibitions were preserved. No production code changed in that correction.

## Remediation traceability (C-01 through C-05)

| Blocker | Resolution | Key changes |
|---|---|---|
| **C-01** â€” Mixed evaluations aborted | **FIXED** | `scripts/evaluate.py`: removed early return; mixed valid/excluded evaluations complete with explicit exclusion artifacts |
| **C-02** â€” Validation failures only in stderr | **FIXED** | `_validated_batches` tracks `candidate_failures`; emitted in `provenance_report.json` via `failure_records` |
| **C-03** â€” Manifest/reuse contract conflicts | **FIXED** | `build_completion_manifest` includes all required fields; `verify_reuse` uses `artifact_index.json` |
| **C-04** â€” Real-gate reporting incomplete | **FIXED** | `_unresolved_real_gates` enumerates all 4 gates; stderr emits complete list |
| **C-05** â€” Historical evidence irrecoverable | **DISPOSITIONED** | Maintainer disposition recorded; never to be silently reconstructed |

## Open risks and gates

The real-evaluation gate remains closed because authorized export, D-14-001, D-14-002, and protocol-approval hashes are unresolved in configuration. Native receipt issue #1793 independently blocks archive and delivery operations. No real evaluation should be attempted, and no publication claim is supportable, until those controls are resolved through their authorized processes.

## Final audit outcome

**T-15-15 independent final audit: PASS.** All requirements (PE-001..015), acceptance criteria (AC-15-001..048), and blocking findings (C-01..C-05) are resolved. Phase 15 is complete and ready for archive (blocked only by administrative receipt #1793).

---

# Phase 16 Implementation Audit Addendum

## Boundary

Phase 16 adds read-only concept evaluation under `src/pada3dacb/evaluation/concepts/`. It does not modify training, adaptation losses, checkpoint selection, data splits, approved Phase 15 predictive behavior, or any earlier scientific method.

The implemented runtime boundary is deterministic synthetic evaluation. Real ADNI/OASIS evaluation remains closed and was not executed. CFS, ACS, PCS, and QIS remain blocked because authoritative equations are unavailable.

## Controls

- Inference is no-grad and requires precomputed `c_target` and `g_bar` artifacts.
- Subject records enforce fixed labels, domains, probabilities, predictions, ROI shape, and SHA-256 provenance.
- Source OOF population and target fold-then-seed aggregation fail closed.
- Statistical resampling is diagnosis-stratified by subject.
- Concept method comparisons use only four valid PADA-3DACB comparators.
- ROI stability preserves separate profile-specific Jaccards and both rank-dispersion statistics.
- Synthetic reporting emits the exact complete tree atomically and verifies read-only reuse.
- AAGN and FasterSNN remain explicit not-applicable rows, never failed concept methods.
- Target labels remain posthoc-only and cannot affect gradients, optimization, scheduling, checkpoints, epoch count, or hyperparameter selection.

## Verification and delivery

Final command evidence is recorded in `specs/phase_16_concept_validation/final_audit.md`. Phase 17 is not started. Native incident #1793 continues to block archive, commit, push, PR, release, and publication independently of technical verification.

## Phase 16 documentation audit (WU-10)

This addendum audits the Phase 16 documentation boundary without changing implementation behavior.

| Control | Documentation evidence | Disposition |
|---|---|---|
| Fixed class order | `docs/CONCEPT_EVALUATION.md`, `docs/PHASE16_REPORT.md` state `CN=0, MCI=1, AD=2` | PASS |
| Target-label firewall | Labels are posthoc-only and excluded from adaptation, checkpoint, and method selection | PASS |
| Read-only artifacts | `c_target` and `g_bar` are precomputed and immutable; training/adaptation mutation is excluded | PASS |
| Metric availability | Undefined correlations retain `constant_roi`, `insufficient_samples`, or `numerical_error` | PASS |
| No causal overclaiming | Documentation rejects causal importance, biomarker, disease-mechanism, and publication claims | PASS |
| Real-data authorization | Synthetic-only lifecycle is documented; real execution remains closed by `authorized: false` and required hashes | PASS |
| Blocked manuscript scores | CFS, ACS, PCS, and QIS are explicitly `BLOCKED` without invented equations | PASS |
| Phase boundary | Phase 17 is explicitly not started | PASS |
| Delivery boundary | Native receipt #1793 is recorded as an administrative blocker, not a scientific result | PASS |

Validation evidence is intentionally bounded: the focused WU-09 suite passed 23 tests, Ruff and diff checks passed, and the full pytest command timed out at 180 seconds. No documentation statement treats that timeout as a passing full-suite result or claims real-data scientific validity.
