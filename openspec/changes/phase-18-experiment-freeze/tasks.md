# Tasks: Phase 18 Scientific Freeze

## Historical planning prerequisites

These rows are preserved as the original planning graph. They describe the approved specification package and are historical prerequisites, not evidence that scientific freeze, real execution, publication, or Phase 19 was approved.

- [x] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [x] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [x] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [x] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [x] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [x] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi` (unavailable; fallback evidence recorded). Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [x] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [x] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [x] **P18-09** Perform independent specification review. Owner: `kimi` (unavailable; fallback via `gentle-ai-explore`/`gentle-ai-verify`). Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

The checked rows record completion of the planning/specification package only. P18-10 remains open because the scientific blockers and real-run authorization are unresolved.

## Implementation closure task graph

This graph supersedes the former planning-only wording for implementation status. Each action has one owner. File ownership is exclusive within this closure graph; evidence-only actions do not claim ownership of runtime files.

| ID | Action | Owner | Depends on | Status | Owns |
|---|---|---|---|---|---|
| C18-01 | phase18-planning-closure | `Codex` | P18-01..P18-09 | complete | `openspec/changes/phase-18-experiment-freeze/state.yaml` |
| C18-02 | scientific-resolution | `maintainer` | C18-01 | blocked | scientific decisions only; no closure file |
| C18-03 | independent-scientific-resolution-review | `gentle-ai-explore`/`gentle-ai-verify` fallback | C18-02 | complete_with_fallback | independent review evidence only; Kimi unavailable |
| C18-04 | canonicalization-and-freeze-core | `Codex` | C18-01 | complete | implementation/test evidence only; no closure file |
| C18-05 | provenance-and-real-data-inspection (metadata-only) | `Codex` | C18-04 | complete_metadata_only | implementation/test evidence only; no real-data artifacts |
| C18-06 | feasibility-and-resource-budget | `Codex` | C18-04 | complete_synthetic_only | implementation/test evidence only; no real resource closure |
| C18-07 | independent-identity-and-feasibility-verification | `gentle-ai-verify` | C18-05, C18-06 | complete_with_findings | independent fallback audit evidence only |
| C18-08 | authorization-and-cli | `Codex` | C18-05, C18-06 | complete_fail_closed | implementation/test evidence only; no real authorization |
| C18-09 | complete-phase18-integration-tests | `Codex` | C18-04, C18-06, C18-08 | complete_focused_verified | implementation/test evidence only |
| C18-10 | documentation | `Codex` | C18-01, C18-03, C18-07, C18-09 | complete | `docs/PHASE18_REPORT.md`, `openspec/changes/phase-18-experiment-freeze/tasks.md` |
| C18-11 | progress-consolidation | `Codex` | C18-04..C18-10 | complete | `specs/phase_18_experiment_freeze/implementation_progress.md`, `openspec/changes/phase-18-experiment-freeze/apply-progress.md` |
| C18-12 | final-independent-audit (Kimi unavailable fallback) | `gentle-ai-verify` | C18-09 | complete_with_limitations | audit result only; no native receipt |
| C18-13 | final-validation | `maintainer` | C18-10, C18-11, C18-12 | blocked_timeout_and_pending_native | no file; full suite timed out and native lifecycle was not run |

## Closure evidence and gates

- Implementation work units WU1-WU5 plus bounded corrections: **complete**.
- Independent fallback verification: **complete with limitations**; Kimi was unavailable and `gentle-ai-verify` performed the fresh verification.
- Focused Phase 18 suite: `python -m pytest -q tests/phase_18/` — **139 passed**, 1 `PytestCacheWarning`.
- Full regression: `python -m pytest -q` — **blocked/unverified** after timeout around 27% with a 1200-second timeout; no pass claim.
- Final documentation/state consolidation: **complete** in this task.
- Scientific freeze: **not approved**; `freeze_approved=false`.
- Real execution and publication: **forbidden/blocked**; `real_execution_authorized=false`, `publication_authorized=false`.
- Native lifecycle receipt and approval: **not run and pending**; no receipt is fabricated.
- Phase 19: **forbidden**.

## Review Workload Forecast

Decision needed before apply: Yes for any future runtime/real-data transition.
Chained PRs recommended: Yes for the historical implementation slices.
400-line budget risk: High for the historical implementation package.

No implementation closure task authorizes real data, publication analysis, native lifecycle mutation, or Phase 19.
