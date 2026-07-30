# Phase 13 Decisions

Phase 13 is authorized as: **Canonical PADA-3DACB Prototype and Pseudo-Label Adaptation**.

## Pre-implementation decisions

| Decision | Status | Evidence |
|---|---:|---|
| Phase 12 CDAN accepted before Phase 13 | Accepted | Engram observation 31 and Phase 13 closure record |
| Ordinary pytest temp root must be repository-local | Accepted | `pyproject.toml` uses `--basetemp=artifacts/pytest-tmp`; `/artifacts/` is ignored |
| Full regression must pass before scientific implementation | Accepted | `python -m pytest -q` passed: 312 passed, 3 warnings |
| Artifact store | Accepted | Hybrid: `specs/phase_13_prototype_pseudo/` plus Engram |
| Execution mode | Accepted | Automatic with gatekeeper |
| Strict TDD | Accepted | Active; full/focused evidence required |

## Scientific decisions pending canonical notebook extraction

The following values MUST NOT be invented. If the active executed notebook path cannot establish any item, the affected implementation is BLOCKED.

- Prototype representation (`z`, `U`, concepts, or another explicit tensor).
- Prototype normalization behavior.
- Prototype distance equation.
- Source and target prototype construction rules.
- Prototype update mode, momentum, absent-class behavior, detach behavior, reductions, epsilons, and coefficient.
- Pseudo-label probability branch, detach behavior, confidence rule, threshold/schedule, objective, class balancing, empty-selection policy, reduction, and coefficient.
- Combined `L_proposed` equation and warm-up/full-stage multipliers.
- Required checkpoint/resume state for the canonical method.

## Blockers

- Engram cloud sync remains blocked by a legacy prompt mutation (`seq=8`, missing `content`). Local Engram read/write is working and is sufficient for Phase 13 action records in this session.
- No Phase 13 scientific implementation may start until `notebook_extraction.md`, `requirements.md`, `design.md`, `tasks.md`, and `acceptance.md` exist and `spec_review.md` approves them.
