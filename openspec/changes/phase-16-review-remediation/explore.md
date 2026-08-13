# Exploration: phase-16-review-remediation

## Status and boundary

This exploration defines the smallest safe remediation scope for the Phase 16 review findings. It does not approve Phase 16, clear the review, archive the change, or authorize Phase 17. Native incident #1793 and escalated receipt `review-a81b3edbc82c5830` remain preserved.

The receipt is high-risk, generation 1, with all four review lenses selected, resolved findings `RISK-001` and `RISK-002`, and terminal state `escalated`. The current Phase 16 verification evidence reports 65 focused tests passing, while the full pytest run timed out and is therefore incomplete evidence.

## Evidence classification

The classifications below are remediation triage, not a review verdict.

| Theme | Classification | Evidence from the allowed surfaces | Safe implication |
|---|---|---|---|
| ROI masks are not bound to the candidate `atlas_hash` | Introduced Phase 16 residual; distinct from resolved RISK-001/RISK-002 | `inference.py` compares runtime masks with `atlas_mgr` masks and ROI order, but `run_inference_on_candidates` does not bind the candidate atlas hash to a hashed canonical atlas artifact. `provenance.py` validates only that the candidate atlas hash looks like a SHA-256 string. | Require an actual canonical atlas artifact/hash match before a candidate can reach inference; fail closed on missing or mismatched binding. |
| Atlas/normalizer ROI-order validation is inconsistent or fail-open | Introduced Phase 16 residual | `_canonical_roi_order_hash` returns `None` when labels are unavailable, which skips the runtime comparison. `DiscoveryConfig` expected hashes are optional, and `discover.py` can retain candidates with empty or malformed metadata. | Centralize strict ROI-order validation and treat absent labels, absent expected hashes for real evaluation, and cross-artifact disagreement as exclusion/blocking conditions. |
| Direct real-evaluation authorization gap | Introduced Phase 16 execution-boundary gap; exact CLI call path was intentionally not read in this exploration | The allowed report/inference surfaces expose callable execution paths without an authorization parameter. Focused mode tests prove the CLI `main` gate for tested paths, but do not prove that direct package entry points cannot bypass it. | Add one authoritative real-run gate used by every real execution entry point, before checkpoint load, inference, statistics, or output publication. |
| `torch.load(weights_only=False)` before provenance validation | Introduced Phase 16 safety defect | Both `discovery.py` and `inference.py` load checkpoints with `weights_only=False` before the candidate has passed strict provenance checks. | Hash/read the file before parsing and use a safe tensor-only load path for untrusted checkpoint content; reject unsupported metadata rather than enabling arbitrary object reconstruction. |
| `overwrite=False` is ignored | Introduced Phase 16 output-contract defect | `report.commit_output` accepts `overwrite` but does not branch on it before replacing an existing recognized output tree. Existing tests cover unknown-path rejection with `overwrite=True`, not the default false behavior. | Default false must preserve the existing tree and fail/reuse explicitly; replacement is permitted only when overwrite is true and the tree is allowlisted. |
| Incomplete discovery/provenance/config validation | Introduced Phase 16 contract gap | `DiscoveryConfig` and `ConceptEvaluationConfig.from_yaml` perform presence/parsing checks but do not consistently validate types, ranges, hash formats, cross-field policy consistency, manifest contents, or artifact assignment. Discovery can construct candidates with weak metadata. | Add the minimum fail-closed validation needed for candidate eligibility, artifact assignment, model configuration, ROI/normalizer/atlas identity, and real-run gate inputs. Do not broaden into unrelated scientific metric validation. |
| Contradictory task/full-suite evidence | Pre-existing Phase 16 process/documentation inconsistency | `openspec/.../tasks.md` marks the final validation row complete, while `verify-report.md` and `final_audit.md` record the full pytest timeout as incomplete evidence. `acceptance.md` retains unchecked acceptance rows. | Reconcile evidence wording in the remediation record; never convert the timeout into a pass or alter the native receipt state. |

## Smallest safe remediation scope

1. **Strict candidate and artifact provenance**
   - Enforce canonical atlas-file/hash binding, normalizer-file/hash binding, and a single ROI label/order hash across checkpoint metadata, normalizer, atlas, and runtime manager.
   - Reject missing, malformed, conflicting, or fail-open metadata before candidates are eligible for inference.
   - Validate the minimum configuration shape and cross-field invariants needed to construct a safe discovery request.

2. **Safe execution boundary**
   - Make checkpoint inspection safe and provenance-first; no `weights_only=False` load of untrusted checkpoint content.
   - Route real-mode execution through one fail-closed authorization contract requiring authorization plus all expected hash evidence.
   - Ensure direct callable entry points cannot perform real inference or report publication without that contract.

3. **Deterministic output semantics**
   - Make `overwrite=False` non-destructive and explicit.
   - Preserve atomic publication, allowlisted-tree checks, manifest-last ordering, and restoration behavior.

4. **Focused evidence reconciliation**
   - Add only behavior-level tests for the above boundaries and record the full-suite timeout as incomplete.
   - Keep the remediation report separate from the escalated Phase 16 receipt; no review lifecycle restart is implied here.

## Work units and ownership

These are serial slices, not parallel edits. Each slice must remain below the 400-authored-line review budget, including its tests.

### Slice A — Candidate provenance and configuration eligibility

- **Owner paths:** `src/pada3dacb/evaluation/concepts/{schemas.py,discovery.py,provenance.py}`.
- **Tests:** `tests/test_concept_{schemas,discovery,provenance}.py`.
- **Contract:** strict hash/type/range checks; actual atlas and normalizer identity; ROI-order agreement; required manifests/artifacts; candidate exclusion with actionable issues.
- **Evidence:** focused discovery/provenance/schema tests, plus negative tests for missing, malformed, and conflicting metadata.

### Slice B — Safe loading and real-run authorization

- **Owner paths:** `src/pada3dacb/evaluation/concepts/inference.py`, the authoritative real-mode entry point (the CLI path must be inspected by the implementation owner before editing), and their focused mode tests.
- **Tests:** `tests/test_concept_inference.py`, `tests/test_concept_modes.py`, and only the smallest required CLI regression test.
- **Contract:** safe checkpoint parsing after file identity is established; no model load or forward pass before authorization/provenance; direct real-mode calls fail closed; synthetic mode remains deterministic and fixture-only.
- **Evidence:** monkeypatched load-order tests, unauthorized direct-call tests, and existing focused inference/mode tests.

### Slice C — Output overwrite and evidence wording

- **Owner paths:** `src/pada3dacb/evaluation/concepts/report.py`; `tests/test_concept_report.py`; the new remediation evidence only.
- **Contract:** default non-overwrite preserves bytes and rejects/reuses explicitly; overwrite requires an allowlisted existing tree; no partial replacement.
- **Evidence:** existing-tree preservation, no-temp-leak, allowlist, rollback, and manifest-last tests. Reconcile timeout wording without claiming a full-suite pass.

Slices are required. Combining all findings would exceed or threaten the 400-line review budget and would mix provenance, execution safety, and output publication risks in one review transaction.

## Explicit non-goals

- No Phase 17 work, paths, production code, or planning.
- No training, adaptation, model architecture, loss, data preprocessing, partition, or real ADNI/OASIS changes.
- No redesign of metrics, aggregation, bootstrap, figures, tables, manuscript scores, or scientific claims.
- No reopening or relabeling resolved `RISK-001`/`RISK-002`; this scope addresses residual and newly classified boundaries only.
- No review lifecycle command, receipt replacement, incident closure, archive, commit, push, PR, release, or publication.
- No claim that Phase 16 is clear or complete; real evaluation remains closed by default.
- No attempt to turn the full-suite timeout into successful validation.

## Acceptance evidence for the remediation

The implementation phase should capture, without claiming it here:

- Focused tests proving candidate atlas hash, atlas/normalizer ROI order, artifact assignment, configuration, and checkpoint metadata fail closed.
- Tests proving file identity/provenance is established before safe checkpoint parsing and that unsafe object loading is not used.
- Tests proving unauthorized real execution is rejected before load/inference/write for both the CLI and direct callable entry points.
- Tests proving `overwrite=False` leaves the existing output tree byte-for-byte unchanged and `overwrite=True` remains allowlist- and rollback-safe.
- Ruff, `py_compile`, and `git diff --check` for the remediation paths.
- A truthful evidence record distinguishing focused passes from the prior full-suite timeout, with receipt `review-a81b3edbc82c5830` and incident #1793 still escalated.
