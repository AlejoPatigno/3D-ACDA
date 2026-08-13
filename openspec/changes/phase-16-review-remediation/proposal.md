# Phase 16 Review Remediation

## Decision summary

Remediate only the remaining Phase 16 review blockers through three serial, independently reviewable slices. The change will make real evaluation fail closed unless an explicitly authorized caller supplies verifiable canonical artifacts, will prevent unsafe checkpoint loading before provenance is established, and will preserve existing valid outputs by publishing new results to deterministic versioned paths.

This proposal does not approve or reopen Phase 16. Native incident `#1793` and escalated review receipt `review-a81b3edbc82c5830` remain unchanged, and the prior full-suite timeout remains incomplete evidence rather than a pass.

## Intent

Close the residual safety, provenance, authorization, output, and evidence-integrity gaps identified by the completed Phase 16 exploration without expanding the scientific feature set or changing the review lifecycle.

## Problem

The current Phase 16 evaluation boundary can admit weakly validated candidate metadata, lacks a single authorization contract for direct real-evaluation entry points, may parse untrusted checkpoints unsafely before provenance validation, and does not honor the non-destructive intent of `overwrite=False`. Its evidence records also risk implying stronger validation than the timed-out full suite supports.

Together, these gaps make a real evaluation difficult to trust: operators cannot prove that the candidate, atlas, normalizer, ROI order, and checkpoint belong together; programmatic invocation may bypass CLI assumptions; existing valid results may be replaced; and scientific evidence may be overstated.

## Target users and operators

- **Evaluation operators** running or supervising real Phase 16 concept evaluation.
- **Trusted CLI and programmatic integrators** that need an explicit, auditable capability to authorize a real run.
- **Scientific reviewers and maintainers** who must verify artifact identity, deterministic publication, and truthful evidence.
- **Incident and release owners** who must preserve the existing escalated receipt and avoid accidental lifecycle transitions.

## Desired business and scientific outcome

After remediation, a real evaluation can proceed only when a trusted caller explicitly authorizes it and all canonical inputs are present with verifiable, mutually consistent hashes. Unauthorized or ambiguous candidates fail before model loading, inference, statistics, or publication. Existing valid results remain intact when overwrite is disabled, while the new evaluation is published at a deterministic versioned location. Evidence clearly distinguishes focused remediation checks from the incomplete full-suite run.

This outcome improves operational safety and scientific traceability; it does not establish scientific validity for a real cohort or clear the existing review escalation.

## Current-state gap

| Area | Current gap | Required outcome |
|---|---|---|
| Candidate eligibility | Hash fields can be syntactically plausible without binding candidates to actual canonical artifacts; missing labels can skip ROI-order comparison. | Candidate eligibility requires actual canonical artifact identity and one consistent ROI order across all relevant inputs. |
| Configuration | Type, range, assignment, and cross-field checks are incomplete or inconsistent. | The minimum configuration needed for safe discovery and real-run authorization is validated fail closed. |
| Real-run authorization | Tested CLI gating does not prove direct callable entry points are protected. | Every real execution entry point enforces one explicit capability contract before side effects. |
| Checkpoint loading | Untrusted checkpoint content may be loaded with `weights_only=False` before strict provenance is established. | File identity is established first, and only a safe tensor-only loading path is permitted. |
| Output semantics | `overwrite=False` does not reliably preserve an existing recognized output tree. | An existing valid result is preserved byte-for-byte and the new evaluation uses a deterministic versioned path. |
| Evidence | Focused passes coexist with a full-suite timeout and contradictory completion wording. | Remediation evidence states exactly what passed and keeps the timeout classified as incomplete. |

## Product and scientific rules

1. **Explicit capability is mandatory for real evaluation.** The CLI or a trusted programmatic caller may enable real evaluation only by supplying an explicit authorization capability. Calling a real-mode function directly is never authorization by itself.
2. **Authorization is necessary but not sufficient.** Real evaluation also requires canonical atlas, normalizer, ROI-order, and checkpoint files whose hashes can be verified and whose identities agree with candidate and runtime metadata.
3. **Real-mode validation fails closed.** Missing, malformed, conflicting, unassigned, unverifiable, or inconsistent provenance/configuration excludes the candidate or blocks the run before checkpoint parsing, inference, statistics, or output publication.
4. **Checkpoint handling is provenance-first and safe.** Establish checkpoint file identity before parsing it. Do not use arbitrary-object reconstruction (`weights_only=False`) for untrusted checkpoint content; reject unsupported metadata or formats.
5. **Synthetic boundaries remain explicit.** Synthetic and validate-only modes may use explicitly designated synthetic fixtures. Synthetic fixtures cannot satisfy or bypass real-mode eligibility.
6. **ROI order is a shared invariant.** Checkpoint metadata, canonical atlas, normalizer, candidate metadata, and runtime manager must agree on one label/order identity for real evaluation.
7. **Non-overwrite is non-destructive.** When `overwrite=False` and an existing valid result is present, preserve it byte-for-byte and publish the new evaluation to a deterministic versioned output path. No partial replacement is allowed.
8. **Overwrite remains constrained.** Any explicit overwrite behavior must retain allowlisted-tree checks, atomic publication, manifest-last ordering, and restoration/rollback guarantees.
9. **Evidence must be literal.** Focused test success may be reported as focused success. The prior full-suite timeout remains incomplete evidence and must never be represented as a pass.
10. **Review state is immutable in this change.** Incident `#1793` and receipt `review-a81b3edbc82c5830` remain escalated; this remediation neither restarts nor relabels them.

## Scope and delivery slices

The work is intentionally split into three serial slices. Each slice includes its focused tests and must remain below the 400-authored-changed-line review budget. A later slice starts only after the preceding slice has produced reviewable evidence.

### Slice A — Candidate provenance and configuration eligibility

**First product slice.** Establish the eligibility boundary before changing execution or publication behavior.

- Validate hash formats, required types/ranges, artifact assignment, manifest requirements, and minimum cross-field invariants.
- Bind candidate atlas and normalizer claims to actual canonical files and verifiable hashes.
- Enforce one ROI label/order identity across checkpoint metadata, normalizer, atlas, candidate metadata, and runtime manager inputs available at eligibility time.
- Exclude candidates with actionable issues when metadata is absent, malformed, conflicting, or unverifiable.
- Add focused negative evidence for each fail-closed boundary.

Expected affected areas: concept evaluation schemas, discovery, provenance, and their focused tests.

### Slice B — Safe checkpoint loading and real-run authorization

- Inspect and route the authoritative CLI real-mode entry point and direct callable paths through one explicit authorization contract.
- Require authorization plus all canonical hash evidence before any real checkpoint load, model construction, forward pass, inference, statistics, or output write.
- Establish checkpoint identity before safe tensor-only parsing; reject formats requiring arbitrary object loading.
- Preserve deterministic synthetic and validate-only behavior using explicit fixtures.
- Add focused load-order and unauthorized direct-call evidence, including the smallest necessary CLI regression coverage.

Expected affected areas: concept inference, the authoritative real-mode entry point, and focused inference/mode/CLI tests.

### Slice C — Deterministic output versioning and truthful evidence

- Preserve an existing valid output tree byte-for-byte when `overwrite=False`.
- Publish the new evaluation to a deterministic versioned output path without partial replacement or temporary-file leakage.
- Preserve allowlist, atomicity, rollback/restoration, and manifest-last guarantees for explicit overwrite behavior.
- Record focused remediation results without claiming that the timed-out full suite passed or that the escalated review is cleared.

Expected affected areas: concept report publication, focused report tests, and remediation evidence artifacts only.

## Affected areas and implications

- **Evaluation API:** real-mode callable entry points gain an explicit authorization requirement; trusted callers must construct and pass the capability and canonical evidence.
- **CLI workflow:** the CLI remains a trusted authorization source only when it deliberately supplies the capability after validating required inputs.
- **Candidate discovery:** previously retained candidates with incomplete or conflicting provenance may now be excluded with actionable diagnostics.
- **Artifact operations:** operators must provide canonical atlas, normalizer, ROI-order, and checkpoint files rather than metadata-only claims for real runs.
- **Output consumers:** repeated non-overwrite evaluations produce versioned result locations; consumers must use the newly returned/published path rather than assume replacement of a fixed directory.
- **Review and support:** evidence becomes easier to audit, but stricter validation may surface existing configuration defects that operators must correct.
- **Scientific interpretation:** no metric, cohort, or scientific claim changes; the remediation strengthens traceability and execution safety only.

## Edge cases

- A hash has valid SHA-256 syntax but does not match the supplied canonical file: reject before loading.
- Atlas, normalizer, checkpoint, candidate, or runtime ROI labels are missing or ordered differently: reject rather than skip comparison.
- A caller invokes a real-mode package function directly without the explicit capability: reject before any side effect.
- A caller has a capability but supplies incomplete or synthetic fixtures for real mode: reject.
- A checkpoint exists and hashes correctly but requires unsafe object reconstruction or contains unsupported metadata: reject without fallback to `weights_only=False`.
- An output directory exists but is invalid or not allowlisted: do not replace it; return an actionable failure according to the publication contract.
- An existing valid result occupies the default path while `overwrite=False`: preserve it and choose the deterministic next versioned path, including under repeated or concurrent attempts.
- Publication fails after staging but before manifest commit: restore/preserve the prior valid tree and leave no partial result presented as complete.
- Focused tests pass while the full suite times out again: report focused passes and the timeout separately; do not infer full-suite success.

## Constraints

- Preserve native incident `#1793` and escalated receipt `review-a81b3edbc82c5830` exactly as existing lifecycle state.
- Do not start, restart, relabel, finalize, or clear a review transaction in this phase.
- Keep the three slices serial and each below 400 authored changed lines, including tests and active evidence content.
- Use strict fail-closed behavior for real evaluation and retain deterministic fixture-only behavior for synthetic/validate-only modes.
- Preserve atomic publication and existing allowlist/rollback protections.
- This proposal authorizes planning only; it does not authorize implementation, approval, archive, commit, push, PR, release, publication, or Phase 17.

## Non-goals

- Unrelated pre-existing defects.
- Training, adaptation, model architecture, loss, preprocessing, partition, or model changes.
- Metrics, aggregation, bootstrap, figure, table, manuscript, or scientific-claim redesign.
- Real cohort evaluation or changes to ADNI/OASIS data workflows.
- Reopening or relabeling resolved findings `RISK-001` and `RISK-002`.
- Treating the full-suite timeout as a pass.
- Phase 17 planning or implementation.
- Closing incident `#1793`, replacing the receipt, or changing the escalated review state.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Authorization capability is forgeable or inconsistently enforced. | Direct callers could bypass the real-run boundary. | Define one authoritative contract, require it at every real entry point, and prove rejection occurs before side effects. |
| Stricter provenance excludes previously accepted candidates. | Operators may see fewer eligible candidates or blocked runs. | Emit actionable exclusion reasons and limit validation to safety-critical eligibility invariants. |
| Safe loading rejects legacy checkpoints. | Some historical artifacts may no longer run. | Fail explicitly; do not add unsafe compatibility fallback. Any migration is a separate scoped decision. |
| Version-path allocation is nondeterministic or races. | Results could collide, overwrite, or become hard to audit. | Define deterministic allocation and atomic publication behavior, with focused repeated/concurrent-path tests where implementation mechanics require them. |
| Slice growth exceeds the review budget. | Review quality degrades and lifecycle handling becomes harder. | Keep ownership serial, stop a slice before 400 lines, and defer non-essential refinements. |
| Evidence wording implies review clearance. | Maintainers may advance Phase 16 or Phase 17 incorrectly. | Name focused evidence precisely and repeat that incident/receipt state remains escalated. |

## Rollback

Rollback is slice-local and must not alter native incident or receipt records. If a slice cannot meet its contract, revert only that slice's code, tests, and newly created remediation evidence, leaving prior slices and existing valid result trees intact. Do not restore unsafe real execution as a compatibility measure; keep real evaluation disabled until a corrected slice is available. Versioned outputs make publication rollback non-destructive because the prior valid result remains the stable fallback.

## Success criteria

The remediation is ready for downstream specification and implementation planning when all of the following are represented as testable requirements:

- Real evaluation is rejected before load, inference, statistics, or write unless an explicit trusted capability and all canonical hash evidence are present.
- Direct invocation alone cannot authorize real evaluation.
- Candidate atlas, normalizer, ROI order, checkpoint, and runtime identities are verified and mutually consistent; missing or conflicting evidence fails closed.
- No untrusted checkpoint is loaded through `weights_only=False`, and file identity is established before safe parsing.
- Synthetic and validate-only modes remain deterministic and use only explicit synthetic fixtures.
- With `overwrite=False`, an existing valid result remains byte-for-byte unchanged and the new result is atomically published at a deterministic versioned path.
- Explicit overwrite retains allowlist, rollback, no-partial-publication, and manifest-last guarantees.
- Focused remediation evidence is truthful, and the prior full-suite timeout remains incomplete evidence.
- Each serial slice stays below the 400-line review budget.
- Incident `#1793` and receipt `review-a81b3edbc82c5830` remain escalated and unchanged.

## Unresolved decisions

None at the product or scientific-policy level. Remaining choices are implementation details to be resolved in specification/design, including the capability representation, canonical hash manifest shape, deterministic version-path format, and concurrency mechanism. Those details must preserve all rules and boundaries above.

## Next step

Create the detailed specification for Slice A and the shared cross-slice invariants. Do not begin implementation or change review lifecycle state from this proposal.
