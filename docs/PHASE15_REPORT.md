# Phase 15 Report

## 1. Phase status

**COMPLETE â€” T-15-15 INDEPENDENT FINAL AUDIT: PASS.**

T-15-01 through T-15-14 complete. T-15-15 final audit returned PASS after remediation of C-01 through C-05. All requirements (PE-001..015), acceptance criteria (AC-15-001..048), and blocking findings resolved. T-15-16 (final-validation) and T-15-17 (OpenSpec mirrors/agent plan maintenance) are the remaining actions. Archive and delivery remain blocked by native receipt #1793 (administrative only). No real-data or publication-performance claim is made.

## 2. SDD documents

Phase artifacts are maintained under `specs/phase_15_predictive_evaluation/` and `openspec/changes/phase-15-predictive-evaluation/`. They include requirements, design, tasks, acceptance criteria, agent plan, decisions, statistical protocol, output schema, proposal, capability specification, and independent specification/statistical reviews (PASS).

## 3. Action graph and ownership

The serial implementation graph was: closure audit â†’ specification â†’ independent review â†’ schemas â†’ discovery/provenance â†’ aggregation â†’ metrics â†’ confusion â†’ bootstrap/inference â†’ independent mathematical verification â†’ tables â†’ report/output/reuse â†’ CLI/config â†’ integration/regressions â†’ documentation â†’ remediation review â†’ final audit â†’ final validation â†’ OpenSpec mirrors.

Conceptual owners followed `agent_plan.yaml`: Claude Code for scientific contracts/documentation, Codex for implementation/tests, Gemini CLI for independent mathematical verification, Kimi for independent scope/statistical review, and OpenCode for orchestration/config/CLI and final commands. Runtime fallbacks preserved conceptual ownership. The exact WU-R22 ownership command reports `actions=14 paths=60 duplicates=0` and `duplicate_paths=[]`.

## 4. Files created or modified

Production Phase 15 behavior resides in `src/pada3dacb/evaluation/`, `scripts/evaluate.py`, and `configs/evaluation/predictive.yaml`. SciPy is a direct runtime dependency; statsmodels remains test/development-only. Focused deterministic tests cover schemas, discovery, provenance, aggregation, metrics, confusion, bootstrap, paired inference, Holm, tables, report state, atomic output, reuse, CLI, integration, modes, boundaries, and regressions.

T-15-14 created/updated:
- `docs/PREDICTIVE_EVALUATION.md` (user-facing guide)
- `docs/PHASE15_REPORT.md` (this report)
- `docs/IMPLEMENTATION_AUDIT.md` (technical audit)

Remediation added:
- `specs/phase_15_predictive_evaluation/maintainer_disposition_c05.md` (C-05 formal disposition)
- `specs/phase_15_predictive_evaluation/final_audit.md` (T-15-15 PASS audit)
- Updated `specs/phase_15_predictive_evaluation/remediation_review.md` (PASS)

## 5. Scientific equations and tensor/data contracts

Class order is fixed: `CN=0`, `MCI=1`, `AD=2`. Subjects are the statistical units. Target probabilities are averaged fold-then-seed; source predictions remain true OOF rows. Directions and checkpoint policies remain isolated. The primary checkpoint is selected only by source-validation macro-F1; target labels cannot influence training or selection.

The evaluator computes 12 aggregate metrics, eight named per-class rows, 3Ã—3 count and row-normalized confusion matrices, deterministic stratified bootstrap intervals, exact paired McNemar, paired stratified bootstrap differences, and six-slot Holm correction families. Canonical subject tables are the sole source for metrics, inference, tables, and figures.

## 6. Configuration decisions

`configs/evaluation/predictive.yaml` selects seven approved methods, both approved directions, folds 0â€“4, seed 42, fixed class order, primary `best_source_f1`, optional sensitivity `last`, and bootstrap default 10,000. Scientific defaults were not invented. The checked-in real gate has four null hashes and `authorized: false`.

## 7. Target-label isolation evidence

Tests verify disjoint target adaptation/evaluation membership, complete target fold/seed ensembles, cross-method subject/label alignment, no target-derived checkpoint policy, and no training imports or invocation from Phase 15. Target evaluation remains monitoring/reporting only.

## 8. Checkpoint and resume behavior

Phase 15 does not train or resume training. It consumes immutable approved exports. Completed evaluation reuse is read-only and requires exact identity, configuration, authorization, version, input, required-file, and hash agreement. It never recomputes metrics or rewrites artifacts.

## 9. Validation evidence

The final successful T-15-15 sequence after all authorized corrections:

| Command | Exit | Result | Duration | Warnings |
|---|---:|---|---:|---|
| `python -m pytest -q tests/test_evaluation_regressions.py tests/test_evaluation_boundaries.py --basetemp=...` | 0 | 7 passed | 4.5 s | 1 cache |
| Ownership validation (`agent_plan.yaml`) | 0 | 14 actions; 60 paths; 0 dupes | 0.2 s | none |
| `python -m pytest -q tests/test_evaluation_*.py` (176 tests) | 0 | 176 passed | 65 s | 1 cache |
| `python -m pytest -q tests/test_all_methods_regression_phase14.py tests/test_proposed_method_cli.py` | 0 | 15 passed | 47 s | 1 cache |
| `python -m pip install -e .` | 0 | Editable build/install succeeded | 12 s | pip notice |
| `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | `0.1.0` | <1 s | none |
| `python -m ruff check .` | 0 | All checks passed | <5 s | none |
| `git diff --check` | 0 | Clean | <1 s | none |

Post-audit WU-R25 validation (no production edits):

| Command | Exit | Result | Warnings |
|---|---:|---|---|
| `python -m pytest -q tests/test_evaluation_*.py` | 0 | **190 passed** | 1 cache |
| `python -m pip install -e .` | 0 | Editable build/install succeeded | pip notice |
| `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | `0.1.0` | none |
| `python -m pytest -q` (full) | 0 | **739 passed** | 7 known |
| `python -m ruff check .` | 0 | All checks passed | none |
| `git diff --check` | 0 | Clean | none |

## 10. Previous-method regressions

The full 739-test suite includes Source-Only, CORAL, MMD, CDAN, PADA-3DACB, AAGN, and Faster-SNN behavior plus target-label isolation and Phase 14 regressions. All regression tests pass.

## 11. Remediation incidents, causes, and corrections

| Unit | Failure observed | Root cause | Correction and retained guard | Evidence |
|---|---|---|---|---|
| C-01 | Mixed evaluations aborted | Early return on empty `included_methods` | Removed early return; mixed evaluations complete with explicit exclusion artifacts | `test_default_mixed_selection_reports_excluded_method_without_its_artifacts` PASS |
| C-02 | Validation failures only in stderr | No capture of `candidate_failures` | Added `candidate_failures` dict; emitted in `provenance_report.json` via `failure_records` | `provenance_report.json` includes excluded candidate issues |
| C-03 | Manifest/reuse contract conflicts | Legacy `evaluation_index.json`; incomplete schema-v2 fields | Aligned manifest to schema-v2; `verify_reuse` uses `artifact_index.json` | Output/reuse suite: 23 passed |
| C-04 | Real-gate reporting incomplete | Combined boolean gate; no enumeration | `_unresolved_real_gates` enumerates 4 gates; stderr emits all unresolved | CLI suite: 27 passed |
| C-05 | Historical evidence irrecoverable | No byte snapshots; Engram inaccessible | Formal maintainer disposition recorded; never silently reconstructed | `maintainer_disposition_c05.md` |

All subsequent remediation failures and their corrections are appended here rather than hidden by aggregate test results.

## 12. Discrepancies and limitations

- No real ADNI/OASIS evaluation was run.
- No real performance, confidence interval, statistical significance, computational cost, or publication result is claimed.
- Missing computational source values remain explicit `not_recorded` nulls.
- `.pytest_cache` cannot be created in this workspace; this does not affect test execution.
- Windows may transiently lock atomic directory replacements; production uses bounded `PermissionError` retry and tests retain strict behavior.
- Native Phase 14 receipt issue #1793 remains an administrative blocker for archive, commit, push, PR, release, and publication.
- Exact retrospective additions-plus-deletions for WU-R01 through WU-R15 cannot be independently reconstructed because per-unit byte snapshots were not preserved. Forecasts, RED/GREEN commands, focused results, and the serial edit record exist, but this report does NOT misrepresent them as exact historical line counts. On explicit maintainer authorization, this is accepted as a documented historical-evidence exception only; it does not waive current defects, tests, scope, ownership, or scientific invariants.

## 13. Installation and computational limitations

Editable installation succeeded with normal dependency resolution; no `--no-deps` fallback was used. Validation was CPU-local and synthetic. Real MRI data, GPU evaluation, real export scale, and runtime/memory benchmarking were not exercised.

## 14. Engram records

Compact records exist for each Phase 15 action, statistical verification, integration slice, stale-guard correction, validation incident, and current apply progress. They contain contracts, files, commands/results, discrepancies, limitations, and next action without private reasoning.

## 15. Next-phase boundary

Phase 15 is complete. T-15-15 PASS unblocks archive and delivery pending native receipt #1793. T-15-16 final-validation and T-15-17 OpenSpec mirrors/agent plan maintenance are the remaining internal actions. Phase 16 production work was not started and requires explicit human approval.
