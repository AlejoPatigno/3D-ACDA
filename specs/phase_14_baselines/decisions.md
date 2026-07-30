# Phase 14 Decisions and Discrepancy Ledger

Project: `pada-3dacb`
Phase: Phase 14 — Canonical Architectural Baseline Migration and Supervised Cross-Cohort Orchestration
Action: `phase13-closure-and-baseline-audit`
Date: 2026-07-23

## Human authorization

- The user explicitly approved moving beyond Phase 13 by authorizing Phase 14 in the orchestrator prompt for this action.
- Phase 13 closure evidence was loaded from Engram topic `sdd/phase-13-prototype-pseudo/archive-report` and `specs/phase_13_prototype_pseudo/archive_report.md`.
- Phase 14 is now the current authorized phase in `AGENTS.md`.
- No Phase 14 production code was created by this action.

## Preflight validation evidence

The most recent Phase 13 closure evidence records:

| Command | Exit code | Result |
|---|---:|---|
| `python -m pytest -q` | 0 | `453 passed, 3 warnings in 479.80s (0:07:59)` |
| `python -m ruff check .` | 0 | `All checks passed!` |
| `git diff --check` | 0 | No output |

This action reused existing full validation evidence and did not rerun full pytest.

## Phase 14 pre-authorization production-file inspection

Inspected target Phase 14 paths:

- `src/pada3dacb/models/baselines/` — absent
- `src/pada3dacb/training/baseline_trainer.py` — absent
- `src/pada3dacb/experiments/baselines.py` — absent
- `configs/baselines/` — absent
- `docs/BASELINES.md` — absent
- `docs/PHASE14_REPORT.md` — absent
- Phase 14-specific tests matching `*phase14*` — absent in the inspected test tree

Observed pre-existing related path outside the requested Phase 14 target path list:

- `configs/experiments/baselines.yaml` exists and must be treated as pre-existing/out-of-scope for this action unless Phase 14 planning explicitly adopts or replaces it.

## Discrepancy ledger

### D-14-001 — Prototype loss weight mismatch

- Repository/current implementation source: `lambda_proto = 1.0`
- Manuscript wording/source: `lambda_proto = 0.2`
- Status: unresolved scientific discrepancy
- Phase 14 handling: do not silently change Phase 13 scientific behavior; carry the discrepancy forward for explicit scientific decision before publication claims or manuscript synchronization.

### D-14-002 — Best-checkpoint criterion wording mismatch

- Repository/current source behavior: source-validation macro-F1-only checkpoint selection.
- Manuscript wording: macro-AUC tie-break wording.
- Status: unresolved manuscript/code discrepancy.
- Phase 14 handling: preserve approved repository invariant unless the user explicitly authorizes a scientific checkpoint-policy change; manuscript text may need correction if code remains authoritative.

### D-14-003 — Native review/receipt status unavailable

- Current native review/receipt inspection: blocked separately with `native-status-unavailable`.
- Status: publication/commit/push blocker, not a Phase 14 specification blocker.
- Phase 14 handling: do not run review lifecycle commands in this action; require parent/orchestrator resolution before commit, push, PR, publication, or release readiness is claimed.

### D-14-004 — Multi-channel MRI input behavior

- Notebook behavior: classification-only baseline loading may truncate a multi-channel tensor to its first channel.
- Production decision: reject tensors whose channel count is not exactly one.
- Why: canonical preprocessing already produces single-channel model-ready tensors, and silent truncation would hide an incompatible input contract.
- Evidence: `ClassificationOnlyMRIDataset` validates `[1,D,H,W]`; focused tests cover rejection of multi-channel inputs.

## Boundaries

- No external architecture search/download was performed.
- No real ADNI/OASIS baseline training was run.
- No Phase 15 work was started.
