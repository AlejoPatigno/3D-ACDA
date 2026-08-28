# Phase 18F — Post-Seed Validation Remediation Acceptance Contract

## Acceptance status

This is a prospective contract. It claims no source change, test result, output publication, evidence result, status update, or review receipt now. Implementation evidence must be written only under the owned `evidence/` paths in this package.

## Package gate

- [ ] The six planning files exist under `specs/phase_18f_post_seed_validation_remediation/`.
- [ ] No path outside that directory was created, modified, staged, committed, or otherwise changed by package creation.
- [ ] The future evidence artifacts, when created, are limited to the exact paths in `requirements.md`; they are not placed in live/frozen evidence locations.
- [ ] No scientific value or completion claim is invented.

## Admission and immutability gate

- [ ] Immutable snapshot A in `evidence/baseline-exclusion-manifest.yaml` exists before any implementation or test maintenance and records path, tracked/untracked state, kind, mode/attributes, size, and SHA-256 for every protected/excluded path and every relevant production/code/config path.
- [ ] The manifest covers the historical freeze document, official untracked POC notebook, runs/results/checkpoints/manifests, unadmitted source/config/tests/notebooks/docs/specs, and Git metadata.
- [ ] `evidence/candidate-admission-manifest.yaml` inventories all tracked and untracked production/code/config paths, not merely `src` tracked diffs.
- [ ] The candidate allowlist explicitly names every admitted publication, focused-test, pre-existing alias, exact stale-test, and prospective-status path, with owner and reason.
- [ ] Each pre-existing alias path is bound to snapshot A and marked as pre-existing; unknown/look-alike aliases are not admitted.
- [ ] Every unlisted path is immutable by default and any unlisted production/code/config change blocks acceptance; final candidate authorization validates the entire allowlist against A.
- [ ] The official notebook and historical freeze document remain byte-for-byte and mode/attribute identical.
- [ ] Runs, results, checkpoints, manifests, configs, notebooks, historical docs/specs, and Git metadata remain unchanged.

## Publication contract gate

- [ ] The final canonical concept-output path, schema, canonical IDs, configuration/artifact hashes, manifests, and checkpoint/resume identities are unchanged.
- [ ] A complete candidate tree is hashed and validated before publication.
- [ ] The sibling, journal, backup, and final path are same-parent and same-volume.
- [ ] The implementation uses the supportable sequence: validated sibling; final to owned backup when present; sibling to final; final revalidation; authenticated backup cleanup.
- [ ] The specification and implementation make no claim of continuous final-destination presence or atomic directory exchange.
- [ ] The final path's absent interval is measured and bounded by `T_absent_max` under normal execution; timeout blocks and invokes conditional rollback.
- [ ] If promotion fails, successful rollback restores the old tree; rollback failure preserves evidence and returns `BLOCKED`.
- [ ] Cooperating readers retry bounded absence and return `unavailable` if the window is exceeded; non-cooperating readers may see old/absent/new but never partial content or an empty-result interpretation.
- [ ] Cross-volume copy, copy-then-delete, delete-then-publish, broad cleanup, and unbounded temporary names are absent.

## Capability, journal, and recovery gate

- [ ] A full minimum-32-byte OS CSPRNG capability is generated per transaction; short reads, unavailable providers, truncation, padding, and reduced entropy fail closed before mutation.
- [ ] The journal is created with exclusive creation in the same parent/volume, has restrictive owner permissions/ACLs, and is durably flushed.
- [ ] The journal binds the complete capability to canonical identity, final relative path, schema/version, owner/attempt/collision tokens, expected manifest hash, same-volume identifiers, type/mode, and state.
- [ ] Recovery accepts only exact grammar plus exact journal/capability, complete manifest, durable `validated` state, and all identity/type/mode/volume checks.
- [ ] Missing, truncated, copied, mismatched, non-exclusively-created, or otherwise uncertain provenance is not recoverable.
- [ ] This provenance is documented as normal stale-process recovery evidence, not complete security against a foreign process able to read/copy/alter filesystem entries or ACLs.
- [ ] Unknown, foreign, and look-alike entries are preserved and surfaced, never promoted, overwritten, renamed, or deleted.
- [ ] A complete authenticated `validated` sibling is promotable only when the final is absent; a valid final always wins.
- [ ] `prepared`, incomplete, corrupt, and interrupted `publishing` states block unless exact revalidation proves safe normal stale recovery.
- [ ] No recovery uses broad globs or deletes all temporary files.

## Path-budget and grammar gate

- [ ] The actual Windows API/runtime and volume are probed using the exact create, journal, validate, rename, rollback, and read operations.
- [ ] UTF-16 path and component budgets are measured; no `260`, `255`, `32767`, or other magic value is assumed without evidence.
- [ ] Both final and sibling path invariants and component fit are proven before mutation.
- [ ] The grammar is `p3dco.<role>.<identity-token>.<attempt-token>[.c<collision-token>].tmp`.
- [ ] Token length is derived from remaining budget after reserving complete grammar/journal/collision overhead.
- [ ] Budget exhaustion rejects before creating or mutating an entry.

## Alias and stale-test gate

- [ ] Existing aliases are integrated only at report/read time, preserving requested spelling, canonical ID, resolution record, schemas, hashes, paths, manifests, and checkpoint identity.
- [ ] Approved alias and canonical request share identity; unknown, ambiguous, case-altered, and look-alike names fail closed.
- [ ] Alias values cannot affect sibling identity or final output path.
- [ ] The exact stale test, assertion/fixture, failing evidence, and contract trace are recorded.
- [ ] If an exact stale failure applies, snapshot B in `evidence/stale-test-production-proof.yaml` captures the complete production/code/config projection after all authorized production and alias implementation is complete and immediately before test maintenance.
- [ ] Only the exact stale assertion/fixture changes.
- [ ] When stale maintenance applies, F7 compares B-before with B-after only; the post-maintenance projection covers tracked and untracked production/code/config paths and is identical by path, kind, mode/attributes, size, and SHA-256.
- [ ] If no exact stale failure applies, the package records F6 not applicable and performs no stale-maintenance comparison.
- [ ] Snapshot B is not substituted for A in final candidate authorization.
- [ ] Any production drift blocks the stale exception. New behavior tests are not stale maintenance.

## Required behavior tests

The focused tests MUST cover:

- [ ] full tracked/untracked candidate admission and unlisted-path rejection;
- [ ] CSPRNG exact length, short-read failure, exclusive journal creation, durable state, and capability mismatch/truncation/copy rejection;
- [ ] long Windows paths, derived budget rejection, and same-volume enforcement;
- [ ] bounded absent-final interval, cooperating reader retry/unavailable, and non-cooperating reader old/absent/new semantics;
- [ ] failed validation, promotion failure, rollback success, rollback failure, and valid-old-tree preservation;
- [ ] authenticated recovery only with final absent and valid-final precedence;
- [ ] foreign/look-alike/case/suffix/symlink/junction/wrong-manifest preservation and surfacing;
- [ ] deterministic collision ordinal selection and budget exhaustion;
- [ ] alias/canonical identity stability and fail-closed alias cases;
- [ ] zero-production-drift proof for exact stale-test maintenance; and
- [ ] Windows integration using the actual filesystem operations.

## Validation commands

After implementation, the owner runs the focused and full validations on the target Windows environment:

```bash
python -m pytest -q tests/test_phase_18f_post_seed_validation.py
python -m pytest -q -m windows_integration tests/test_phase_18f_post_seed_validation.py
python -m pytest -q tests/test_evaluation_display_names.py tests/test_evaluation_tables.py
python -m pytest -q
git diff --check
git status --short --untracked-files=all
```

The final candidate's admission and exclusion comparisons MUST validate the entire allowlist against immutable snapshot A. The stale-test comparison MUST use only snapshot B's just-before/just-after full production/code/config projections. A command that hashes only `git diff -- src/pada3dacb` is not evidence and cannot satisfy acceptance. The full suite must pass without skipping Windows integration or suppressing the known failure.

## Final candidate and receipt gate

- [ ] `evidence/validation-manifest.yaml` binds all focused/full-suite results, A-bound allowlist authorization, B-only stale-test post-proof, reader/absence-window/rollback assertions, and exclusion comparison.
- [ ] Exactly one final candidate is frozen in `evidence/final-candidate-manifest.yaml` with immutable path, byte, mode/attribute, canonical identity, changed-path, and evidence hashes.
- [ ] No candidate changes after freeze.
- [ ] Exactly one new native high-risk 4R receipt covers that candidate, using `review-risk`, `review-resilience`, `review-readability`, and `review-reliability`.
- [ ] Any post-review candidate or evidence-scope change invalidates the receipt and requires explicit maintainer action.

## Fail-closed policy

Missing, conflicting, stale, ambiguous, foreign, or failed evidence is `BLOCKED`. No plausible path, alias spelling, test expectation, target result, or historical document may substitute for the required manifest, provenance, rollback, admission, or post-maintenance proof.
