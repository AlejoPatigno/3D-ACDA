# Phase 18 Independent Specification Review Ledger

- Target: `phase-18-experiment-freeze`
- Round: 2 (re-judgment after bounded Round-1 correction)
- Review type: blind dual scientific/specification review
- Real execution: forbidden
- Publication analysis: forbidden
- Phase 19: forbidden
- Native review lifecycle: not run
- Verdict: `JUDGMENT: APPROVED` for the corrected specification package only; real execution/publication remain blocked

## Findings

| ID | Lens | Location | Severity | Status | Evidence / impact |
|---|---|---|---|---|---|
| JUDGE-A-001 | judgment-day | `specs/phase_18_experiment_freeze/decisions.md:90` | BLOCKER | fixed | `lambda_proto=1.0` in the primary path/configuration conflicts with `lambda_proto=0.2` in a later helper/default. Publication matrix authorization cannot safely proceed until authoritative evidence or an explicit maintainer decision resolves the value. |
| JD-B-001 | judgment-day | `specs/phase_18_experiment_freeze/scientific_resolution.md:61` | CRITICAL | fixed | Mandatory method parameters are omitted from the unresolved ledger: checked-in CORAL adaptation weight, MMD weight/bandwidths, and CDAN weight/GRL/discriminator settings are null and rejected by current validators. Resolving existing blockers could still leave the matrix unrunnable or force invented values. |
| JD-B-002 | judgment-day | `specs/phase_18_experiment_freeze/experiment_matrix.md:12` | CRITICAL | fixed | Matrix direction IDs use `ADNI_to_OASIS`/`OASIS_to_ADNI`, while cited canonical configuration/evaluation enum uses lowercase `adni_to_oasis`/`oasis_to_adni`. No hash-bound mapping is defined, risking parser/provenance mismatch or silent remapping. |
| JD-B-003 | judgment-day | `specs/phase_18_experiment_freeze/real_run_gate.md:32` | CRITICAL | fixed | Aggregate assignment hashes do not prove subject-set disjointness. A mandatory intersection check over hash-verified manifest contents is required to prevent target evaluation subjects from appearing in target adaptation. |
| JD-B-004 | judgment-day | `specs/phase_18_experiment_freeze/experiment_matrix.md:21` | CRITICAL | fixed | `last` is described as an evaluation projection but is represented as an identical matrix row without row-kind or parent-training identity. A literal executor could schedule 140 trainings instead of 70 trainings plus 140 projections. |
| JD-B-005 | judgment-day | `specs/phase_18_experiment_freeze/resource_budget.md:29` | CRITICAL | fixed | Faithful synthetic calibration is permitted to resolve real per-cell wall time, contradicting `feasibility_protocol.md:43`, which says synthetic feasibility cannot establish real throughput. Synthetic observations must not close real wall-time fields. |
| JD-B-006 | judgment-day | `specs/phase_18_experiment_freeze/provenance_freeze.md:36` | CRITICAL | fixed | Canonical JSON lacks an exact version and rules for number formatting, negative zero, Unicode escaping, and separators. Equivalent payloads could hash differently, breaking authorization/resume identity. |
| JD-B-007 | judgment-day | `specs/phase_18_experiment_freeze/freeze_schema.md:67` | WARNING | info | State vocabulary permits later `COMPLETED`, but `MatrixRow` excludes it and fixes `completion_allowed=false`; a later authorized completed row would require an undocumented schema change. |
| JD-B-008 | judgment-day | `openspec/changes/phase-18-experiment-freeze/tasks.md:8` | WARNING | info | OpenSpec and local tasks assign overlapping specification files to different owners, violating the exclusive single-owner contract and risking conflicting future work. |
| JD-B-009 | judgment-day | `specs/phase_18_experiment_freeze/manuscript_alignment.md:18` | WARNING | info | A manuscript row uses a compound status rather than one exact allowed token (`MATCH`, `MANUSCRIPT_OUTDATED`, `REPOSITORY_OUTDATED`, `UNRESOLVED`), preventing deterministic validation. |

## Round-1 correction notes

The original severe evidence and impact above are retained verbatim. The bounded correction fixed the open severe rows as follows:

- `JUDGE-A-001`: `lambda_proto=0.2` versus `1.0` remains explicitly `unresolved_blocking`; matrix compilation and real-run authorization reject unresolved values.
- `JD-B-001`: the unresolved ledger now enumerates CORAL weight, MMD weight/kernel/bandwidths, and CDAN weight/GRL/discriminator settings; loader validation is required and invented defaults are forbidden.
- `JD-B-002`: direction IDs are parser-bound canonical lowercase identifiers; display/uppercase aliases are rejected without remapping.
- `JD-B-003`: hash-verified adaptation/evaluation manifest contents are intersected at subject-identity level; aggregate hashes alone are insufficient.
- `JD-B-004`: training and checkpoint-projection rows use `row_kind` and `parent_training_id`; exactly one training invocation is required per method/direction/fold/seed cell.
- `JD-B-005`: synthetic feasibility is limited to shape/contract validation and synthetic diagnostics; it cannot resolve real timing or resource fields.
- `JD-B-006`: `phase18.canonical-json.v1` now defines deterministic numeric, negative-zero, Unicode, and separator rules plus normative conformance vectors; absent authoritative vectors remain `unresolved_blocking`.

## Synthesis

- Confirmed severe findings entering the approved correction transaction: `JUDGE-A-001` and `JD-B-001` through `JD-B-006`.
- Severe correction status: all seven rows are `fixed` after the bounded Round-1 documentation correction. Round-2 Judge A approved and verified JUDGE-A-001. Round-2 Judge B verified JUDGE-A-001 and JD-B-001 through JD-B-006, but marked JD-B-006 as a regression because canonicalization vectors remain normative documentation rather than executed implementation evidence; retain this as an implementation-gated blocker for future canonicalization code.
- Informational findings: `JD-B-007` through `JD-B-009`; warnings remain `info` and were not changed or scheduled for correction.
- No implementation, real-data execution, publication analysis, or Phase 19 action was performed.
- The package remains blocked and `real_execution_authorized=false`, `publication_authorized=false`.

## Required next action

The bounded Round 1 correction and required dual re-judgment are complete. Specification review is terminally approved for the corrected planning package only. JD-B-006 remains implementation-gated. Do not begin implementation, real execution, publication analysis, or Phase 19 without separate authorization gates and implementation-level verification.
