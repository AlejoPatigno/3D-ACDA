# Phase 18 — Future Execution Plan

## Status

This is an ordered plan for a later, separately authorized transaction. It is not executed now. No real data, feasibility probe, publication analysis, or Phase 19 action is permitted by this document.

## Stage 0 — Preserve and inspect

- Confirm the workspace is dirty and preserve unrelated changes.
- Read the Phase 18 decisions and Phase 17 closure as immutable inputs.
- Do not normalize, clean, stage, or modify unrelated files.
- Confirm the OpenSpec state remains `blocked_planning` with the four authorization boundaries.

## Stage 1 — Resolve science before runtime

- Obtain an authoritative decision for `lambda_proto=0.2` versus `1.0`; until then the matrix compiler and real-run gate reject authorization.
- Obtain explicit human selection of the publication ablation subset, or record that no ablation subset is included.
- Confirm fixed coefficients, method inventory, parser-bound direction IDs `adni_to_oasis`/`oasis_to_adni`, folds `0..4`, seed policy `[42]`, epoch values, checkpoint policy, and statistical endpoints.
- Supply checked-in CORAL/MMD/CDAN parameter fields and loader-validation evidence; no missing field may be filled with an invented default.
- Do not use target metrics, target labels, or publication outcomes to make any selection.

## Stage 2 — Bind immutable inputs

- Supply exact split and assignment manifests for both directions and all folds/seeds.
- Prove target adaptation/evaluation disjointness by intersecting subject identities from hash-verified manifest contents; aggregate hashes alone are insufficient.
- Identify and hash atlas/ROI order/masks, concept normalizer/targets, Jacobian artifacts, preprocessing identity, model/configuration, code/environment, and approved command.
- Record privacy/data-access approval and sanitized path mappings.
- Any absent or conflicting input blocks the transition.

## Stage 3 — Synthetic feasibility

- Run only the synthetic faithful-shape protocol in `feasibility_protocol.md`.
- Exercise matrix/schema, target firewall, fixed epochs, checkpoint selection, resume, hashing, and failure semantics.
- Record synthetic device, memory, storage, and duration observations only as engineering diagnostics; they MUST NOT resolve real wall-time or other resource fields.
- Update the resource budget only with observed evidence; otherwise retain unresolved placeholders.

## Stage 4 — Independent review and authorization

- Obtain independent specification review of the complete package.
- Record all review findings and resolutions outside runtime output.
- Create the hash-bound real-run gate manifest only when science, provenance, budget, privacy, and command identity are complete.
- Obtain explicit human authorization. Real-run authorization does not authorize publication or Phase 19.

## Stage 5 — Preflight-only command

The future implementation must support exact planning/validation selectors based on existing repository command conventions:

```text
--config PATH --method METHOD --direction DIRECTION --fold FOLD --seed SEED
--artifact-index PATH --output-root PATH --dry-run | --validate-only
```

Preflight must finish before any real input is opened. A real mode must additionally consume the authorization manifest and verify all hashes. No command is run by this action.

## Stage 6 — Sequential cell execution

- Execute only the authorized complete matrix in deterministic order.
- Keep each parser direction ID, fold, seed, method identity, and row kind isolated. Execute exactly one training invocation per method/direction/fold/seed; materialize `last` as a linked checkpoint projection using `parent_training_id`, never as another training.
- Preserve fixed epochs and source-validation macro-F1-only checkpoint selection.
- Keep target evaluation monitoring-only and disjoint from adaptation.
- Write atomically, flush history, and update the artifact index only after byte/hash verification.

## Stage 7 — Failure and retry

- Preserve a structured row for every failure or interruption.
- Resume only with an identity-matching checkpoint and unchanged immutable inputs.
- Do not silently overwrite, skip, average away, or mark a failed fold complete.
- Resource changes, coefficient changes, assignment changes, or command changes require a new identity and renewed authorization.
- There is no automatic retry policy until a maintainer selects and records one.

## Stage 8 — Closure

- Verify every authorized row and artifact hash independently.
- Keep incomplete/failed rows visible.
- Produce no publication tables or claims unless a separate publication gate is approved.
- Keep Phase 19 forbidden and do not archive this change as scientifically approved while blockers remain.
