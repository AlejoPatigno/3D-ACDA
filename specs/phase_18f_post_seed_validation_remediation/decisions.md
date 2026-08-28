# Phase 18F — Post-Seed Validation Remediation Decisions

## Decision status

These decisions authorize only a later bounded implementation. They do not claim that remediation, tests, evidence, status, or a review receipt exists or has passed.

### D-F-001 — Final post-seed boundary

Phase 18F follows reporting-only Phase 18E. It admits one final candidate and one high-risk 4R receipt after validation. Existing alias changes remain an unreviewed baseline until that single review.

**Disposition:** `AUTHORIZED_FOR_PLANNING`.

### D-F-002 — Narrow Windows fix

The known failure is Windows path length in `src/pada3dacb/evaluation/concepts/report.py`. The remedy is bounded temporary sibling naming and a safer publication boundary only. Scientific identifiers, schemas, hashes, canonical paths, and values are not shortened or redefined.

**Disposition:** `SCOPE_BOUNDARY`.

### D-F-003 — No impossible atomic-exchange claim

The filesystem contract is a same-volume two-rename sequence, not an atomic directory exchange and not continuous final-path presence: validated sibling; final to same-parent owned backup; sibling to final; final revalidation; authenticated backup cleanup. The final path may be absent between the two renames. `T_absent_max` is measured/enforced during normal execution; it is not a guarantee against process termination, power loss, or an uncooperative filesystem.

Cooperating readers use a shared lock and bounded retry, then return `unavailable`. Non-cooperating readers may observe old, absent, or new, never partial content, and must not interpret absence as empty. Promotion failure gets a conditional rollback; rollback failure preserves both sides and returns `BLOCKED`.

**Disposition:** `REQUIRED_WITH_EXPLICIT_LIMITS`.

### D-F-004 — Derived path budget

The target Windows API/runtime and volume must be probed with the exact operations. UTF-16 final, sibling, component, journal, and collision budgets are derived; no `260`, `255`, `32767`, or other magic length is assumed. Grammar rejection occurs before mutation.

**Disposition:** `REQUIRED_AND_TESTED`.

### D-F-005 — Deterministic bounded grammar

The sibling grammar is:

```text
p3dco.<role>.<identity-token>.<attempt-token>[.c<collision-token>].tmp
```

The identity token is budget-derived lowercase base32 over canonical identity only. Attempt and collision tokens are lowercase base36. Aliases, absolute paths, timestamps, labels, and scientific values are excluded.

**Disposition:** `APPROVED_FOR_IMPLEMENTATION`.

### D-F-006 — Recovery requires durable exclusive provenance

A recoverable transaction requires a complete minimum-32-byte OS CSPRNG capability with exact-length/no-truncation verification, a same-parent same-volume journal created by exclusive create, restrictive owner permissions/ACLs, durable journal/state flushes, and exact binding to canonical identity, final relative path, schema/version, tokens, expected manifest, type/mode, and same-volume identifiers. Only a complete sibling with exact journal/capability and durable `validated` state may be recovered when final is absent.

This evidence supports normal stale-process recovery only. It is not complete cryptographic authentication against a foreign process with filesystem authority to read/copy/alter entries. If foreign activity cannot be ruled out, the entry is preserved, surfaced, and recovery blocks.

**Disposition:** `FAIL_CLOSED`.

### D-F-007 — Foreign and look-alike entries are preserved

Unknown files/directories, symlinks, junctions, case variants, alternate suffixes, wrong manifests, missing journals, copied capabilities, and other look-alikes are never promoted, overwritten, renamed, or deleted. Exact owned cleanup is allowed only after authenticated distinctness from the final tree and journal-state authorization. Broad cleanup is forbidden.

**Disposition:** `PRESERVE_AND_SURFACE`.

### D-F-008 — Full candidate admission replaces `src` diff

Immutable snapshot A is captured before any authorized implementation or test-maintenance edit. The candidate admission manifest inventories tracked and untracked production/code/config paths, records path, state, kind, mode/attributes, size, and SHA-256, and binds the explicit allowlist to A. The allowlist admits only named publication/focused-test paths, baseline-enumerated pre-existing alias paths, the exact stale-test path, and one status surface. Unlisted paths are immutable. A `git diff -- src` hash is not sufficient.

After all authorized production and alias implementation is complete, snapshot B is captured immediately before the exact test-only edit. The stale-test proof compares B-before with B-after only, including untracked paths. Any byte, path, kind, mode, size, or hash drift blocks stale maintenance; B does not authorize the final candidate, which must validate the entire allowlist against A.

**Disposition:** `REQUIRED_AND_ADMISSION_BOUND`.

### D-F-009 — Owned evidence paths

Implementation evidence is assigned to these exact paths and nowhere else:

- `evidence/baseline-exclusion-manifest.yaml` — snapshot A, owned by the evidence verifier and captured before all work;
- `evidence/candidate-admission-manifest.yaml` — A-bound allowlist, owned by the evidence verifier;
- `evidence/stale-test-production-proof.yaml` — snapshot B before/after, owned by the stale-test maintainer after production/alias implementation is complete;
- `evidence/validation-manifest.yaml`; and
- `evidence/final-candidate-manifest.yaml`.

These are under `specs/phase_18f_post_seed_validation_remediation/`; naming them does not claim that they exist now. Live/frozen evidence locations remain immutable.

**Disposition:** `PATH_BOUND`.

### D-F-010 — Acyclic test-maintenance proof

The acyclic dependency is snapshot A baseline exclusion -> A-bound candidate admission -> implementation and behavior tests -> alias integration -> snapshot B immediately before exact stale-test maintenance -> B-after projection and B-only proof -> complete validation, with final candidate authorization against A. F7 depends on the B-before capture/edit and compares only B; it never feeds admission or its own predecessor. New behavior tests are implementation work, not stale maintenance.

**Disposition:** `ACYCLIC_AND_REQUIRED`.

### D-F-011 — Alias projection only

Existing aliases may be wired only at read/report time. Requested spelling, canonical ID, and existing resolution record remain visible; canonical schemas, hashes, paths, manifests, checkpoints, and historical records remain unchanged. Alias tokens never enter publication identity.

**Disposition:** `COMPATIBILITY_PRESERVED`.

### D-F-012 — Prospective status only

A later implementation may update one pre-identified prospective status surface. It may not rewrite the historical freeze document, historical status, seed history, or scientific result. If no safe surface exists, status is blocked rather than invented.

**Disposition:** `PROSPECTIVE_ONLY`.

### D-F-013 — One final receipt

After validation, freeze one exact candidate with complete path/byte/mode and evidence manifests, then route exactly one native high-risk 4R receipt using risk, resilience, readability, and reliability. Any later candidate or evidence-scope change invalidates the receipt and requires explicit maintainer action. This package does not execute lifecycle commands.

**Disposition:** `ONE_RECEIPT_AFTER_VALIDATION`.

### D-F-014 — Distinct admission snapshots

Snapshot A is the immutable pre-work baseline/exclusion snapshot and the authority for final candidate allowlist validation. When exact stale-test maintenance applies, snapshot B is the just-before/just-after stale-test maintenance projection captured only after authorized production and alias implementation is complete. F7 compares only B-before with B-after; it cannot authorize scope or replace A. If no exact stale failure applies, F6 is explicitly not applicable and no B comparison is performed. This boundary is explicit, owner-bound, and acyclic.

**Disposition:** `REQUIRED_AND_SEPARATE`.

### D-F-015 — Bounded F1 lineage-gap exception

The maintainer explicitly authorizes a bounded F1 lineage-gap exception because F1r3 exact bytes are unavailable. The recorded F1r3 hash is identifier-only; no r3→r4 preservation, byte-equivalence, or delta claim is authorized. The exception permits current candidate admission against immutable Snapshot A only and requires independent current-candidate re-attestation. It does not waive any later validation, final-candidate, or native-receipt requirement. Any change to the admitted candidate identities, path modes or attributes, or Snapshot-A identity invalidates the attestation.

**Disposition:** `AUTHORIZED_FOR_CURRENT_F1_ADMISSION_ONLY`.

### D-F-016 — Decision-authority path without status duplication

The maintainer authorizes admission of `specs/phase_18f_post_seed_validation_remediation/decisions.md` as one A-bound decision-authority path in F1 revision 6. Its manifest entry must carry the exact Snapshot-A identity and the current candidate reconciliation under the existing admission schema. This path records authorizations and decisions only; it is not a status surface and must not duplicate the P4 F8 record. `specs/phase_18f_post_seed_validation_remediation/tasks.md` remains P4's sole F8 status surface.

**Disposition:** `AUTHORIZED_AS_DECISION_AUTHORITY_ONLY`.

## Discrepancy and unknown register

### X-F-001 — Exact existing alias paths

Paths must be enumerated in the candidate-admission manifest before editing. No alias file is presumed admissible.

**Disposition:** `BLOCKED_UNTIL_BASELINE_MANIFEST`.

### X-F-002 — Exact stale prototype-test path

The stale path and assertion remain unknown until a focused failure identifies them. No broad prototype-test maintenance is authorized.

**Disposition:** `BLOCKED_UNTIL_EXACT_FAILURE`.

### X-F-003 — Prospective status surface

The status destination must be an existing, explicitly admitted prospective surface. No substitute status file is invented.

**Disposition:** `BLOCKED_UNTIL_SURFACE_IDENTIFIED`.

### X-F-004 — Windows path policy value

The numeric budget remains environment-specific until the exact-operation probe passes. No numeric value or digest length is asserted here.

**Disposition:** `BLOCKED_UNTIL_PROBE_EVIDENCE`.

### X-F-005 — Filesystem threat boundary

The CSPRNG capability and exclusive journal provide durable provenance for ordinary stale-process recovery. They cannot, by themselves, authenticate an adversarial foreign writer with sufficient filesystem authority. Such uncertainty is preserved/surfaced and blocked rather than described as complete security.

**Disposition:** `EXPLICIT_LIMIT`.

## Non-goals reaffirmed

No new scientific configuration, training/evaluation, result rewrite, notebook/output/checkpoint/manifest mutation, schema/hash/path migration, historical freeze edit, Git mutation, broad test repair, or multiple review receipt is authorized.
