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

The real-evaluation gate remains closed because authorized export, D-14-001, D-14-002, and protocol-approval hashes are unresolved in configuration. In this historical Phase 15 snapshot, native receipt issue #1793 was an independent administrative blocker for archive and delivery operations. No real evaluation should be attempted, and no publication claim is supportable, until the scientific controls are resolved through their authorized processes.

## Final audit outcome

**T-15-15 independent final audit: PASS.** All requirements (PE-001..015), acceptance criteria (AC-15-001..048), and blocking findings (C-01..C-05) are resolved. Phase 15 is complete; its historical delivery snapshot recorded administrative receipt #1793 as the only archive blocker.

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

Final command evidence is recorded in `specs/phase_16_concept_validation/final_audit.md`. Phase 17 is governed separately, with synthetic-only implementation and closure evidence recorded in its own addendum. The Phase 16 snapshot recorded native incident #1793 as an administrative delivery issue, independently of technical verification.

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
| Phase boundary | Phase 17 synthetic-only scope is separately implemented and closed | PASS |
| Delivery boundary | Historical Phase 16 receipt #1793 is administrative provenance, not a scientific result or a current Phase 17 receipt | PASS |

Validation evidence is intentionally bounded: the focused WU-09 suite passed 23 tests, Ruff and diff checks passed, and the full pytest command timed out at 180 seconds. No documentation statement treats that timeout as a passing full-suite result or claims real-data scientific validity.

---

# Phase 17 Implementation Audit Addendum

## Scope and evidence boundary

This addendum audits the Phase 17 synthetic-only ablation implementation. It is appended to the previous Phase 16 audit and does not rewrite or retract earlier claims. Phase 17 does not load real ADNI/OASIS data, report ablation performance, generate publication metrics, or start Phase 18.

The authoritative post-Phase17 evidence includes **119 focused Phase 17 tests passed**, `python -m ruff check .` passed, `git diff --check` passed, and the complete current repository suite **1178 passed with 7 warnings** in 1012.14s. The existing **1059-test** repository result with a clean basetemp is the pre-Phase17 baseline only; it is not used as current validation evidence.

## Exact implementation paths

| Boundary | Current path | Audit disposition |
|---|---|---|
| Typed registry contracts | `src/pada3dacb/ablations/schemas.py` | Defines exact IDs, classifications, dispositions, canonical coefficients, model variants, target fields, matrices, assignments, canonical JSON, and SHA-256 helpers. |
| Candidate registry | `src/pada3dacb/ablations/registry.py` | Retains six approved IDs and visible blocked/unresolved records; aliases are not silently resolved. |
| Pure resolver | `src/pada3dacb/ablations/resolver.py` | Performs approval, one-intervention, coefficient, architecture, matrix, assignment, firewall, and phase-boundary checks before data loading. |
| Output metadata contracts | `src/pada3dacb/ablations/outputs.py` | Defines checkpoint, history, prediction, monitoring, equivalence, and artifact-index metadata constraints. |
| Synthetic ablation orchestration | `src/pada3dacb/experiments/ablations.py` | Owns dry-run, validate-only, deterministic synthetic lifecycle, atomic artifacts, identity hashes, resume validation, and blocked real-run/publication behavior. |
| CLI entrypoint | `scripts/run_ablations.py` | Delegates to the Phase 17 synthetic-only CLI; it exposes no publication-evaluation or Phase 18 switch. |
| Mean-pool composition | `src/pada3dacb/models/ablations/mean_pooling.py` | Implements only `z = U.mean(dim=1)` and uniform `alpha = 1/K` over the current PADA-3DACB boundary. |
| Output path helper | `src/pada3dacb/experiments/run_manifest.py` | Produces `ablations/<candidate>/<direction>/seed_<seed>/fold_<fold>` without discovery or directory creation. |
| Synthetic configuration | `configs/experiments/ablations.yaml` and `configs/ablations/` | Declares synthetic-only execution, both directions, folds `0..4`, seed `42`, explicit epochs, and canonical primary coefficients. |

The implementation composes around the existing PADA-3DACB model and trainer/loss paths. The Phase 17 implementation does not add `ContextualROIEncoder`, `ctx_enc`, a Full/Lite runtime switch, or a duplicate trainer.

## Protected methods and boundaries

The following protected method identities remain regression-guarded and are not redefined as ablations:

- `source_only` / PADA-3DACB Source-Only;
- `coral` / `PADA-3DACB + CORAL`;
- `mmd` / `PADA-3DACB + MMD`;
- `cdan`;
- `prototype_pseudo` / PADA-3DACB;
- `aagn` / AAGN / ROI-aware gating;
- `faster_snn` / FasterSNN;
- Phase 15 predictive evaluation;
- Phase 16 concept evaluation.

The corresponding regression surface is `tests/phase_17/test_protected_methods_regression.py`, which checks the prior CLI identities, adaptation settings, method-scoped output paths, baseline registry separation, and Phase 15/16 boundary absence. Shared target-adaptation enforcement remains in `src/pada3dacb/training/uda_trainer.py`; the approved prototype/pseudo-label integration remains in `src/pada3dacb/adaptation/prototype_pseudo.py`. Their Phase 17 changes are guarded by the focused composition, mathematical, firewall, lifecycle, and protected-method tests.

## Candidate and architecture controls

The registry records these exact interventions only: `no_proto` sets `lambda_proto=0.0`; `no_pl` sets `lambda_pl=0.0`; `no_cons` sets `lambda_cons=0.0`; `no_concept` sets `lambda_cbm=0.0`; `no_anat` sets `lambda_anat=0.0`; and `mean_pool` replaces only the retained aggregator with the exact uniform mean. The canonical primary `lambda_proto=1.0` is preserved; the later helper value `0.2` remains unresolved.

The resolver rejects multiple interventions, unapproved overrides, incomplete matrices, overlapping target assignments, target supervision, contextual variants, unsupported aliases, the unproven `no_domain_adaptation` Source-Only claim, and unauthorized real/publication requests. The target adaptation contract is exactly `x`, `subject_id`, `subject_hash`, and `cohort`; target evaluation is disjoint and labeled `MONITORING ONLY — NOT A TRAINING LOSS`.

## Identity, lifecycle, and artifact controls

The implementation uses SHA-256 over canonical UTF-8 JSON with sorted keys, stable list ordering, no timestamps in hashed payloads, and `phase17.canonical-json.v1`. Registry, candidate, resolved configuration, model variant, source split, target adaptation, target evaluation, and precomputed-artifact identities are carried through the lifecycle. Artifact indexes verify written file hashes and roles.

Synthetic lifecycle checkpoints capture fixed-epoch position, history position, source-validation best value, RNG/loader state, identity data, empty target checkpoint-selection state, and `contains_mri_data: false`. The best checkpoint is selected only by source-validation macro-F1, and training continues through all explicit warm/full epochs. Resume validates the complete identity and artifact set before continuing; a mismatch fails closed without overwriting another run. Target-adaptation prediction output is not produced.

## Validation and remaining limitations

The focused Phase 17 evidence is 119 passing tests across registry/resolver, loss composition, architecture, CLI, mathematical reference, firewall, lifecycle, and protected-method regression coverage. Ruff and diff checks passed. This evidence validates synthetic contracts and implementation boundaries only. It does not establish real-cohort performance or publication validity.

The pre-Phase17 baseline of 1059 tests passed with clean basetemp and is retained as historical baseline evidence only. The authoritative post-Phase17 full repository rerun is recorded below as 1178 passed. No current documentation claim treats the baseline as post-implementation validation. The former Phase 16 native incident `#1793` and approved receipt `review-79ee2a4308d2010c` are historical administrative provenance only, not a current Phase 17 receipt; no current Phase 17 native review receipt was created because the parent bootstrap timed out. Phase 18 has not started.

# Phase 17 Closure Addendum

## Closure disposition and evidence correction

This addendum is appended after the existing Phase 16 and Phase 17 audit content. It does not rewrite or reorder that content. The Phase 17 implementation, validation evidence, and final independent review are complete. The requested Kimi final-audit action was executed through the documented fallback because Kimi was unavailable; `specs/phase_17_ablations/final_audit.md` records the result accurately as **PASS**.

The authoritative current post-Phase17 full result is `python -m pytest -q`: exit 0, **1178 passed, 7 warnings, 1012.14s (0:16:52)**. The warnings were four sklearn `UndefinedMetricWarning` instances, two preprocessing standard-deviation warnings, and the existing Windows pytest-cache permission warning. The earlier **1059 passed** result is retained as the pre-Phase17 baseline only. The earlier statement that the full suite had not yet been rerun was a prior snapshot; this current parent-provided rerun is authoritative. The Phase 17 focused recheck passed **119 tests with 0 warnings**. `python -m pip install -e .` exited 0; import/version exited 0 with version `0.1.0`; Ruff passed; and `git diff --check` passed.

## Candidate, firewall, and lifecycle confirmation

The six approved IDs remain exactly `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, and `mean_pool`, with the one-component interventions and preserved components documented in `docs/PHASE17_REPORT.md`. `no_domain_adaptation` remains `BLOCKED_NOT_PROVEN`; `no_ctx_encoder` remains equivalent to the existing no-context method but invalid as a runnable identity; `identity_ctx` is helper-only; `full` is invalid after the architecture revision; aliases and `lambda_proto = 0.2` remain unresolved or unsupported. The target firewall remains exact and target evaluation remains labeled `MONITORING ONLY — NOT A TRAINING LOSS`.

Executed lifecycle evidence covers 60 synthetic CLI plans (six candidates × five folds × two directions), approved validate-only behavior, exit-2 rejection for `no_domain_adaptation`, `no_ctx_encoder`, and invalid requests, one complete lifecycle pass, five target-firewall tests, 66 prior-method/Phase 15/Phase 16 targeted tests, and 43 registry/CLI tests. No real data was loaded. SHA-256 canonical identity and identity-bound resume controls remain in force.

## Administrative and authorization boundary

The former incident `#1793` is historical administrative context, not a scientific result. The approved receipt named in the historical audit content is Phase 16 provenance only, not a current Phase 17 receipt; no current Phase 17 native review receipt was created because the parent bootstrap timed out, and this addendum does not fabricate one. Real ADNI/OASIS training or evaluation and publication metrics or conclusions remain unauthorized. Phase 18 has not started. The final independent fallback review returned PASS; the next action is STOP and await explicit human approval.

**Current lifecycle authority:** Current status is defined by `openspec/changes/phase-17-ablations/state.yaml` and `docs/IMPLEMENTATION_AUDIT.md`. Historical Phase 16 mirrors are time-scoped records, not current lifecycle authority.

**Phase 17 final closure: COMPLETE / closed after independent fallback review PASS by `gentle-ai-verify` (requested `kimi` unavailable); OpenSpec is `completed / phase17-closed`, Engram closure record 571 is saved, exact current validation remains 1178 full-suite passes with 7 warnings and 119 isolated Phase 17 passes, and the next action is STOP / await explicit human approval without starting Phase 18.**
