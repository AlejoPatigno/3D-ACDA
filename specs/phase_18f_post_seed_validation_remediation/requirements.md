# Phase 18F — Post-Seed Validation Remediation Requirements

## Status and decision boundary

Phase 18F is a prospective, implementation-authorizing specification. It does not edit source, tests, outputs, notebooks, checkpoints, manifests, status files, the historical freeze document, or Git state. The later implementation may produce evidence only at the owned paths named in this package.

The objective is one validated final candidate followed by one new high-risk native 4R receipt. Phase 18E remains reporting-only. Existing report-time aliases are an unreviewed input and may be integrated only without expanding their meaning.

The known full-suite failure is the Windows path-length failure in `src/pada3dacb/evaluation/concepts/report.py`. The fix is limited to the bounded concept-output publication boundary; it must not shorten scientific IDs, schemas, hashes, or canonical paths.

## Protected authorities

1. `docs/EXPERIMENT_FREEZE_PRE_3D_ACDA.md` is historical and immutable.
2. `train-pada3dacb-baselines-ablation (2).ipynb` is frozen, official, untracked evidence and remains byte-for-byte unchanged.
3. Live/frozen runs, results, checkpoints, manifests, source/configuration values, and seed evidence remain authoritative.
4. The existing alias diff is an input baseline, not permission to alter canonical identity.
5. Any path not admitted by the candidate-admission manifest is excluded by default.

## Owned evidence paths

The implementation MUST write no generated evidence outside this directory. The following paths are owned and reserved; they do not exist or claim results merely because this specification names them:

| Evidence | Exact path | Owner | Timing |
|---|---|---|---|
| Baseline exclusion manifest (snapshot A) | `specs/phase_18f_post_seed_validation_remediation/evidence/baseline-exclusion-manifest.yaml` | evidence verifier | before any authorized implementation or test-maintenance edit |
| Candidate admission manifest | `specs/phase_18f_post_seed_validation_remediation/evidence/candidate-admission-manifest.yaml` | evidence verifier | after baseline snapshot, before any test maintenance or implementation edit |
| Validation manifest | `specs/phase_18f_post_seed_validation_remediation/evidence/validation-manifest.yaml` | evidence verifier | after all maintenance and validation |
| Final-candidate manifest | `specs/phase_18f_post_seed_validation_remediation/evidence/final-candidate-manifest.yaml` | receipt controller | immediately before the one native review |
| Stale-test production proof (snapshot B before/after) | `specs/phase_18f_post_seed_validation_remediation/evidence/stale-test-production-proof.yaml` | stale-test maintainer | after all authorized production/alias implementation, immediately before, and immediately after the exact test-only edit |

These are implementation evidence artifacts, not live/frozen scientific evidence. They must be path/mode/attribute/size/hash bound and must not be placed in `runs/`, `results/`, `checkpoints/`, `manifests/`, `.git/`, or another repository location.

## Normative requirements

### Snapshot separation invariant

Snapshot A is the immutable baseline/exclusion snapshot captured before any authorized implementation or test-maintenance edit. It contains the baseline identities needed to authorize the complete candidate allowlist and excluded/unlisted paths. When exact stale-test maintenance applies, snapshot B is a distinct complete production/code/config projection captured only after all authorized production and alias implementation is complete and immediately before the exact stale-test edit. F7 compares B-before with B-after only. Final candidate authorization validates the entire allowlist against A and never substitutes B for A; this separation is mandatory and acyclic.

### R-F-001 — Narrow scope and explicit admission

The implementation is limited to:

- bounded same-volume concept-output publication siblings and their transaction journal;
- integration of already-existing report-time aliases;
- exact stale prototype-test maintenance after the admission and proof gates; and
- one explicitly identified prospective status surface, if safe.

Before editing, the admission manifest MUST enumerate every tracked and untracked production, code, and configuration path in the relevant repository surfaces. Each record includes repository-relative path, tracked/untracked state, kind, mode/attributes, size, SHA-256, baseline identity, disposition, owner, and reason. An untracked path is not exempt from admission.

The manifest MUST contain an explicit candidate allowlist. Only these may change: the named publication source path, newly required focused behavior tests, the exact pre-existing alias paths enumerated from the baseline, the exact stale-test path if later proven stale, and the pre-identified prospective status surface. Every pre-existing alias path must be marked `pre_existing_alias: true` and carry its baseline hash/mode. Unknown or look-alike alias paths are not admitted. All other tracked and untracked production/code/config paths are immutable and any path outside the manifest is a scope violation.

Snapshot A and the admission manifest together define the complete baseline production/code/config surface and explicit allowlist; they are not a `src`-only or tracked-diff check. When exact stale-test maintenance applies, the stale-test proof MUST capture snapshot B after all authorized production and alias implementation and immediately before the exact test-only edit, then compare B-before with B-after by path, kind, mode/attributes, size, and SHA-256; equality is required. A test-only edit that adds, removes, renames, or changes any production/code/config path is blocked by F7. Final candidate authorization separately validates every admitted delta and every excluded/unlisted path against immutable A.

### R-F-002 — Supportable same-volume publication sequence

The implementation MUST build and validate a complete candidate tree before publication and create its controlled sibling in the final output's parent and volume. It MUST use only the approved same-volume rename/replacement primitives; cross-volume copy, copy-then-delete, delete-then-publish, and unbounded temporary names are forbidden.

The contract MUST NOT claim continuous final-destination presence or an atomic directory exchange. The supportable sequence is:

1. create the authenticated sibling and durable journal with exclusive creation;
2. write and hash the complete candidate tree;
3. durably record `validated` and revalidate sibling, final path, parent, and same-volume identity;
4. acquire the publisher lock and rename the existing valid final tree to an owned same-parent backup, if one exists;
5. rename the validated sibling to the final path;
6. revalidate the final tree and durably record `published`; and
7. remove an authenticated backup only after successful final validation, using the approved cleanup policy.

Between steps 4 and 5 the final path can be absent. The implementation MUST measure that interval, enforce a configured `T_absent_max`, and return `BLOCKED` if the interval exceeds the bound. This is a service bound under non-crash execution, not a guarantee against arbitrary OS termination, power loss, or an uncooperative filesystem.

Rollback is conditional and explicit: if promotion fails after the old tree was moved, restore the authenticated backup to the final path with the same-volume primitive. A successful rollback restores the old tree and returns structured failure. If rollback fails or the state is ambiguous, preserve the backup and candidate, do not guess, and return `BLOCKED`; no unconditional rollback or continuous-presence claim is permitted.

Cooperating readers use the existing reader/shared-lock convention and retry a bounded number of times when the final path is absent. Non-cooperating readers may observe old, absent, or new, but never a partially published tree; they must treat absence as `unavailable`, never as an empty result. Readers never inspect siblings or backups.

### R-F-003 — Derived Windows path budget

The implementation MUST derive a host/API/volume-specific budget from a passing probe of the exact create, journal, validate, rename, rollback, and read operations. It MUST measure UTF-16 code units, final-path fit, sibling-path fit, and component fit. It MUST NOT assume `260`, `255`, `32767`, or any magic value without evidence.

The invariant is:

```text
utf16_units(parent_absolute_path) + 1 + utf16_units(name) <= verified_path_budget
utf16_units(sibling_component) <= verified_component_budget
```

The final path and every collision candidate are checked independently. Grammar overhead, attempt, collision, journal suffix, and required capability metadata are reserved before deriving the digest-token length. If the grammar cannot fit, reject before filesystem mutation.

### R-F-004 — Deterministic bounded sibling grammar

The sibling name MUST be:

```text
p3dco.<role>.<identity-token>.<attempt-token>[.c<collision-token>].tmp
```

`identity-token` is lowercase unpadded base32 derived from a cryptographic digest of canonical final-output identity, canonical relative path, and publication schema/version. `attempt-token` and `collision-token` are lowercase base36. No display alias, absolute path, scientific value, raw label, timestamp, or unbounded method name enters the name or digest. The final canonical output path remains unchanged.

### R-F-005 — Durable exclusive transaction provenance

A controlled transaction is recoverable only with all of the following durable provenance:

- an OS CSPRNG capability of at least 32 bytes generated for this transaction; the provider MUST return the full requested byte count, and the implementation MUST fail closed rather than truncate, pad, retry into a shorter value, or silently reduce entropy;
- a journal created with an exclusive-create primitive (`CREATE_NEW`/equivalent) before the sibling is created, in the same parent/volume, with restrictive owner permissions/ACLs;
- the complete, untruncated capability encoded in the journal and bound to canonical identity, final relative path, schema/version, attempt/collision tokens, owner marker, expected manifest hash, same-volume file identifiers, and state;
- durable flush of journal creation and each state transition according to the platform durability convention; and
- an exclusive-create result and journal sequence that bind the sibling to that transaction, rather than directory-name resemblance alone.

The journal states are `prepared`, `validated`, `publishing`, `published`, and `aborted`. Recovery accepts only an exact grammar match plus a complete sibling, exact journal/capability match, valid expected manifest, correct type/mode, same-volume evidence, and a durable `validated` state. A sibling with no journal, a missing/truncated/mismatched capability, non-exclusive provenance, or uncertain ownership is not recoverable.

This capability is evidence for normal stale-process recovery, not proof against an adversary able to read, copy, replace, or alter filesystem entries or ACLs. The implementation MUST state that limitation. If foreign activity cannot be ruled out, it MUST preserve and surface the entries and block; it must never promote or delete them.

### R-F-006 — Foreign collisions and conservative recovery

Unknown, foreign, or look-alike controlled siblings are preserved and surfaced, never promoted, renamed, overwritten, or deleted. This includes exact-looking names with wrong metadata, alternate suffixes, case variants, symlinks, junctions, directories, files, missing journals, copied capabilities, and any entry whose provenance is not exact.

An exact owned sibling may be recovered only when the final path is absent, the sibling is complete, the journal is durable and exclusively created, the capability is full and exact, the state is `validated`, and all identity/manifest/type/mode/volume checks pass. If the final output is valid, it wins and the sibling is left untouched or marked for later authenticated cleanup. `prepared`, `publishing`, incomplete, corrupt, and ambiguous states block unless exact revalidation proves a safe normal stale-process recovery; no state is guessed through.

Cleanup may remove only an authenticated owned sibling or backup after it is proven distinct from the final tree and permitted by the journal state. No broad glob or delete-all-temp recovery is allowed. Normal stale-process recovery and adversarial foreign-entry handling are separate: the former may use exact durable provenance; the latter is preserved/surfaced and fail-closed.

### R-F-007 — Alias integration without identity mutation

Already-existing report-time aliases may be wired only at read/render time. Canonical IDs, schemas, field names, hashes, paths, manifests, checkpoint/resume identities, stored reports, and historical records remain unchanged. Projected output retains requested spelling, resolved canonical ID, and the existing alias-resolution record. Unknown, ambiguous, look-alike, and unapproved names fail closed. Alias tokens never enter the publication digest.

### R-F-008 — Exact stale-test maintenance and post-proof

Stale maintenance is conditional on an exact failing test and expectation traced to the already-existing alias/publication contract. The stale maintainer may edit only that assertion/fixture, and only after the baseline exclusion manifest and candidate admission manifest are complete, all authorized production and alias implementation is complete, and snapshot B is captured immediately before the edit at `evidence/stale-test-production-proof.yaml`.

After the test-only edit, the maintainer MUST recompute the full production/code/config projection and compare it with B-before only, by path, kind, mode/attributes, size, and SHA-256. Equality is the B-only post-maintenance proof. F7 does not authorize candidate scope or the final candidate. Any production drift, including an untracked production/config file, blocks and requires explicit scope action. New behavior tests are implementation changes, not stale maintenance.

### R-F-009 — Evidence immutability and manifests

`baseline-exclusion-manifest.yaml` MUST capture immutable snapshot A before edits and enumerate protected paths/classes plus the baseline identities for the complete relevant production/code/config surface, including the historical document, official notebook, live/frozen runs/results/checkpoints/manifests, all unadmitted source/config/tests/notebooks/docs/specs, and Git metadata, with path, kind, mode/attributes, size, and SHA-256.

`candidate-admission-manifest.yaml` MUST enumerate the complete tracked/untracked production/code/config surface and explicit A-bound allowlist. `stale-test-production-proof.yaml` MUST bind snapshot B-before and B-after and identify that F7 compares only B. `validation-manifest.yaml` MUST bind focused/full-suite results, A-bound final candidate authorization, publication sequence/reader/rollback assertions, B-only stale-test post-proof, and excluded-path comparison. `final-candidate-manifest.yaml` MUST bind the exact final path/byte/mode set, complete changed-path set, canonical hashes, and evidence hashes. No generated artifact is written elsewhere.

### R-F-010 — Prospective status only

A status update may touch only one pre-identified prospective status surface. It must describe Phase 18F evidence prospectively and must not rewrite the historical freeze document, seed history, or scientific results. If no safe surface exists, status is `BLOCKED`; no substitute is invented.

### R-F-011 — One final candidate and one receipt

After all tests and evidence pass, freeze exactly one candidate. The final-candidate manifest and its complete changed-path manifest are the sole review input. Any later path, byte, mode, evidence-scope, or status-surface change invalidates the candidate and receipt and requires explicit maintainer action. This package does not run the lifecycle.

## Required safety tests

The future focused tests MUST cover: full admission of tracked/untracked production/code/config paths; zero production drift after stale-test maintenance; full CSPRNG capability length and short-read failure; exclusive journal creation and durable state transitions; missing/truncated/copied capability rejection; preservation/surfacing of foreign and look-alike entries; authenticated stale recovery only with final absent; valid-final precedence; bounded absent-final interval and reader retry/unavailable semantics; conditional rollback and rollback-failure blocking; same-volume replacement; path-budget rejection before mutation; collisions; symlinks/junctions; alias identity stability; and Windows integration using the actual filesystem operations.

## Non-goals

No new run, scientific comparison, metric/model/loss change, evaluation-math change, schema/hash/canonical-path migration, notebook/output/checkpoint mutation, historical rewrite, broad test repair, Git mutation, or multiple review receipts is authorized.
