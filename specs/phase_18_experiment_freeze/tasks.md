# Phase 18 — Dependency-Ordered Planning Tasks

## Execution boundary

This is a planning ledger. It does not authorize implementation, real data, publication analysis, or Phase 19. The current specification transaction has one writer; the owners below are the intended owner for a later action and MUST NOT run concurrently or edit outside `owns`.

## Ordered action graph

| ID | Action | Depends on | Owner | Owns | Required result |
|---|---|---|---|---|---|
| P18-A1 | Requirements contract | Phase 17 closure and decisions | `claude-code` | `specs/phase_18_experiment_freeze/requirements.md` | Normative scope, values, boundaries, and non-goals. |
| P18-A2 | Technical design | P18-A1 | `opencode` | `specs/phase_18_experiment_freeze/design.md` | Architecture, data flow, tradeoffs, and verification boundary. |
| P18-A3 | Acceptance contract | P18-A1, P18-A2 | `claude-code` | `specs/phase_18_experiment_freeze/acceptance.md` | Executable Given/When/Then acceptance criteria. |
| P18-A4 | Scientific resolution ledger | P18-A1 | `claude-code` | `specs/phase_18_experiment_freeze/scientific_resolution.md` | Explicit values, classifications, references, and blockers. |
| P18-A5 | Deterministic matrix | P18-A4 | `claude-code` | `specs/phase_18_experiment_freeze/experiment_matrix.md` | Complete method/direction/fold/seed schema with no completed rows. |
| P18-A6 | Provenance and hash freeze | P18-A4 | `claude-code` | `specs/phase_18_experiment_freeze/provenance_freeze.md` | Immutable inputs, hash algorithm, privacy, and identity envelope. |
| P18-A7 | Freeze schema | P18-A5, P18-A6 | `claude-code` | `specs/phase_18_experiment_freeze/freeze_schema.md` | Run, row, state, artifact, and failure vocabularies. |
| P18-A8 | Synthetic feasibility protocol | P18-A7 | `gemini-cli` | `specs/phase_18_experiment_freeze/feasibility_protocol.md` | Faithful-shape synthetic procedure and observation schema; no execution. |
| P18-A9 | Resource budget | P18-A8 | `opencode` | `specs/phase_18_experiment_freeze/resource_budget.md` | Conservative/nominal placeholders and unresolved hardware gates. |
| P18-A10 | Real-run authorization gate | P18-A6, P18-A9 | `opencode` | `specs/phase_18_experiment_freeze/real_run_gate.md` | Fail-closed authorization contract and CLI requirements. |
| P18-A11 | Future execution plan | P18-A5, P18-A10 | `opencode` | `specs/phase_18_experiment_freeze/execution_plan.md` | Ordered future preflight/run/retry/closure procedure. |
| P18-A12 | Manuscript alignment audit | P18-A4 and available manuscript evidence | `kimi` | `specs/phase_18_experiment_freeze/manuscript_alignment.md` | Status table using all four alignment statuses; no manuscript rewrite. |
| P18-A13 | Agent plan | P18-A1 through P18-A12 | `opencode` | `specs/phase_18_experiment_freeze/agent_plan.yaml` | Machine-readable ownership and dependencies. |
| P18-A14 | OpenSpec mirrors | P18-A1 through P18-A13 | `opencode` | `openspec/changes/phase-18-experiment-freeze/proposal.md`, `design.md`, `tasks.md`, `state.yaml`, `specs/experiment-freeze/spec.md` | Consistent OpenSpec planning record; blocked until independent approval. |
| P18-A15 | Independent specification review | P18-A14 | `kimi` | No implementation path; review output is external to this ownership set | Approve, reject, or return the freeze with explicit findings. |
| P18-A16 | Human scientific resolution | P18-A15 | `maintainer` | No file ownership granted by this action | Resolve lambda, publication ablation subset, assignments, hardware, and manuscript discrepancies. |
| P18-A17 | Implementation planning transition | P18-A16 | `opencode` | No runtime ownership granted here | Update authorization only after evidence; otherwise remain blocked. |

## Dependency and stop rules

- A blocked dependency stops every dependent action.
- P18-A16 MUST NOT select values from target metrics.
- P18-A17 MUST NOT start Phase 19 or real execution.
- A future implementation plan must split schema/firewall, synthetic lifecycle, provenance, CLI gate, and regression work into separate ownership units.
- No action may own `decisions.md`, `.git/gentle-ai`, native receipts, or unrelated dirty paths.

## Review Workload Forecast

The complete specification package is documentation-heavy and exceeds a comfortable single review slice if implemented as one change. No runtime code is included here.

Decision needed before apply: Yes
Chained PRs recommended: Yes
400-line budget risk: High

Recommended future slices:

1. protocol/schema/provenance documents;
2. synthetic feasibility and resource observation tooling;
3. authorization gate and CLI integration;
4. independent verification and only then any real-run request.

No apply action is authorized by this ledger until the delivery strategy and slice boundary are resolved by the orchestrator.
