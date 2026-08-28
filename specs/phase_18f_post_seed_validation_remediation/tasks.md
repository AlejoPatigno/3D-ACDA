# Phase 18F — Post-Seed Validation Remediation Task Plan

## Task status and ownership

The original task contract is prospective. This addendum records only the verified F5–F9 evidence state; it does not claim implementation completion, output publication, status rewrite, review receipt, staging, or commit.

One owner writes each path. The evidence verifier is read-only with respect to source/tests. The publication owner owns production behavior and new behavior tests together. The alias owner may touch only baseline-enumerated existing alias paths and directly affected projection tests. The stale maintainer may touch only one exact stale assertion/fixture after the admission gate. The receipt controller freezes one final candidate and routes one receipt.

## Owned evidence paths

| Artifact | Path | Owner |
|---|---|---|
| Baseline exclusion (snapshot A) | `specs/phase_18f_post_seed_validation_remediation/evidence/baseline-exclusion-manifest.yaml` | evidence verifier |
| Candidate admission (A-bound allowlist) | `specs/phase_18f_post_seed_validation_remediation/evidence/candidate-admission-manifest.yaml` | evidence verifier |
| Stale-test proof (snapshot B before/after) | `specs/phase_18f_post_seed_validation_remediation/evidence/stale-test-production-proof.yaml` | stale-test maintainer |
| Validation | `specs/phase_18f_post_seed_validation_remediation/evidence/validation-manifest.yaml` | evidence verifier |
| Final candidate | `specs/phase_18f_post_seed_validation_remediation/evidence/final-candidate-manifest.yaml` | receipt controller |

No generated evidence may be written anywhere else.

## Candidate admission contract

Snapshot A is the immutable baseline/exclusion snapshot captured before any implementation or test-maintenance work. It covers the protected/excluded paths and the complete relevant tracked/untracked production/code/config surface needed to authorize the candidate. The candidate-admission manifest binds every path and disposition to A's path, kind, mode/attributes, size, and SHA-256 identity; A is never rewritten.

The candidate-admission manifest is a complete inventory of tracked and untracked production/code/config paths. It records path, tracked state, kind, mode/attributes, size, SHA-256, baseline identity, disposition, owner, and reason. It covers all relevant production/code/config roots, not only `src` and not only `git diff`; untracked production/config files are included.

The manifest explicitly allowlists the publication source path, new focused behavior tests, every pre-existing alias path, the exact stale-test path when identified, and the one prospective status surface. Existing alias paths require an A-bound baseline hash/mode and `pre_existing_alias: true`. Every other path is immutable or blocked.

When exact stale-test maintenance applies, snapshot B is a separate complete production/code/config projection captured only after all authorized production and alias implementation is complete and immediately before the exact stale-test edit. The stale-test proof records B-before and B-after; F7 compares only those two B projections. B never replaces A and cannot authorize candidate scope. Final candidate authorization separately validates the entire allowlist and every excluded/unlisted path against immutable A.

## Acyclic dependency graph

```text
F0 baseline exclusion
  -> F1 candidate admission bound to immutable snapshot A
  -> F2 path budget and transaction capability contract
  -> F3 bounded publication implementation
  -> F4 publication/recovery/reader behavior tests
  -> F5 existing alias integration
  -> F6 exact stale-test maintenance (conditional)
  -> F7 post-maintenance production proof
  -> F8 prospective status decision/update (conditional)
  -> F9 complete validation and exclusion proof
  -> F10 one final candidate freeze
  -> F11 one native high-risk 4R receipt
```

F6 is deliberately after F1, F4, and F5: it captures snapshot B immediately before the exact stale-test edit, then performs that edit. F7 compares only B-before with B-after and must not be used to authorize candidate scope. F6 must not depend on F7. No task depends, directly or indirectly, on its own post-proof.

## Actions

### F0 — Baseline exclusion (snapshot A)

**Owner:** evidence verifier. **Depends on:** all seeds finished and explicit final-remediation authorization.

- [ ] Capture immutable snapshot A before any implementation or test-maintenance write: path, tracked/untracked state, kind, mode/attributes, size, and SHA-256 for every protected/excluded path and every relevant production/code/config path.
- [ ] Include the historical freeze document, official untracked notebook, live/frozen runs/results/checkpoints/manifests, unadmitted source/config/tests/notebooks/docs/specs, and Git metadata.
- [ ] Record the existing alias diff without editing it.
- [ ] Record the known Windows failure without changing its evidence.
- [ ] Stop on any request to touch protected evidence.

**Gate:** baseline manifest exists at the owned path and has complete exclusion coverage.

### F1 — Candidate admission bound to snapshot A

**Owner:** evidence verifier. **Depends on:** F0.

- [ ] Enumerate all tracked and untracked production/code/config paths, including paths not shown by a tracked `src` diff.
- [ ] Create the explicit allowlist and owner/disposition for every candidate path; bind each baseline identity to immutable snapshot A, and require baseline proof for pre-existing aliases.
- [ ] Do not create snapshot B here: no stale-test projection is valid until all authorized production and alias implementation is complete.
- [ ] Enumerate the exact stale-test path only when a focused failure identifies it.
- [ ] Name the one prospective status surface or record that status is blocked.

**Gate:** no path can enter implementation or test maintenance without A-bound admission; the complete allowlist is recorded.

### F2 — Path budget, capability, and journal contract

**Owner:** publication implementation owner. **Depends on:** F1.

- [ ] Probe the actual Windows API/runtime and volume in an isolated test location for UTF-16 path/component, create, journal, rename, rollback, and read behavior.
- [ ] Derive the grammar budget and reject before mutation when it cannot fit.
- [ ] Implement an OS CSPRNG capability request of at least 32 bytes, exact-length verification, and short-read/unavailable failure.
- [ ] Specify exclusive journal creation, restrictive ACL/owner policy, durable flushes, state transitions, manifest binding, and same-volume identifiers.
- [ ] Document the limitation that this provenance supports normal stale-process recovery but cannot prove authenticity against a filesystem adversary who can copy/alter entries.

**Gate:** verified budget and exact capability/journal contract are recorded and tested.

### F3 — Bounded publication implementation

**Owner:** publication implementation owner. **Depends on:** F2.

- [ ] Preserve the canonical final path, output schema, canonical IDs, hashes, and checkpoint identity.
- [ ] Render the bounded sibling grammar from canonical identity only.
- [ ] Create the journal and sibling with exclusive creation beside the final path on the same volume.
- [ ] Validate and durably record a complete candidate tree before publication.
- [ ] Implement publisher-lock sequence: final to owned backup, validated sibling to final, final revalidation, authenticated backup cleanup.
- [ ] Enforce `T_absent_max`; implement conditional rollback and `BLOCKED` on rollback failure/ambiguity.
- [ ] Ensure foreign/look-alike entries are never promoted, overwritten, renamed, or deleted.

**Gate:** the supportable two-rename sequence is implemented without a continuous-presence or atomic-exchange claim.

### F4 — Behavior, recovery, and reader tests

**Owner:** publication implementation owner. **Depends on:** F3.

- [ ] Test long paths, derived budget exhaustion, and rejection before mutation.
- [ ] Test full CSPRNG length, short-read failure, exclusive journal creation, durable states, and capability mismatch/truncation/copy rejection.
- [ ] Test valid old tree preservation, bounded absent-final interval, cooperative reader retry/unavailable semantics, non-cooperating reader old/absent/new semantics, and conditional rollback including rollback failure.
- [ ] Test authenticated `validated` recovery only with final absent and valid-final precedence.
- [ ] Test preservation/surfacing of foreign files/directories, symlinks/junctions, case variants, alternate suffixes, look-alikes, and wrong-manifest entries.
- [ ] Test deterministic collision ordinals, same-volume enforcement, and actual Windows replacement operations.

**Gate:** all safety cases pass; no test deletes or adopts an unknown entry.

### F5 — Existing alias integration

**Owner:** alias integration owner. **Depends on:** F1, F3, and F4.

- [ ] Touch only paths explicitly marked as pre-existing aliases in the admission manifest and directly affected projection tests.
- [ ] Preserve requested spelling, canonical ID, resolution record, schemas, hashes, paths, manifests, and checkpoint identity.
- [ ] Prove approved alias/canonical identity equality, alias non-interference with publication identity, and fail-closed unknown/ambiguous/look-alike handling.
- [ ] Prove the change remains report/read-time only.

**Gate:** alias integration is projection-only and has no unadmitted path or canonical identity drift.

### F6 — Snapshot B and exact stale-test maintenance (conditional)

**Owner:** stale-test maintainer. **Depends on:** F1, F4, F5, and an exact focused stale-failure record. **Must not depend on F7.**

- [ ] Record the exact test, assertion/fixture, old expectation, and trace to an already-existing alias/publication contract; if no exact stale failure exists, record F6 as not applicable and do not create B.
- [ ] Verify the path is explicitly admitted as the exact stale-test path when F6 applies.
- [ ] After all authorized production and alias implementation is complete, capture snapshot B as the complete production/code/config projection immediately before the test-only edit in `evidence/stale-test-production-proof.yaml`.
- [ ] Apply only the assertion/fixture edit after B-before is frozen.
- [ ] Do not add new behavior tests here; those belong to F4.

**Gate:** when F6 applies, B-before is captured at the correct boundary and the test-only edit is completed; when not applicable, the explicit decision skips B/F7 stale proof. No claim of production safety is made until the applicable F7 gate.

### F7 — Post-maintenance production proof against snapshot B

**Owner:** stale-test maintainer writes the proof; evidence verifier reads it read-only. **Depends on:** F6 (or explicit F6 not-applicable decision). If F6 is not applicable, F7 records that no stale-maintenance comparison is required and does not substitute A.

- [ ] When F6 applies, recompute the complete tracked/untracked production/code/config projection immediately after the test-only edit.
- [ ] Compare path, kind, mode/attributes, size, and SHA-256 with B-before only; do not compare this stale-maintenance proof with F1 or snapshot A.
- [ ] Append the B-before/B-after result and hashes to `evidence/stale-test-production-proof.yaml`; this path remains owned by the stale-test maintainer.
- [ ] Mark `BLOCKED` on any production drift, including an untracked file or mode/path change.

**Gate:** when F6 applies, B-before equals B-after exactly, or stale maintenance is rejected; when F6 is not applicable, the explicit no-comparison decision passes. F7 does not authorize the final candidate.

### F8 — Prospective status (conditional)

**Owner:** status owner. **Depends on:** F7 and the pre-identified status-surface decision.

- [ ] Update only the named prospective surface.
- [ ] Record Phase 18F state and evidence references prospectively.
- [ ] Never rewrite the historical freeze document or historical status.
- [ ] If no safe surface exists, record `BLOCKED` in validation evidence rather than inventing a file.

**Gate:** status scope is prospective and admitted.

### F9 — Complete validation and exclusion proof

**Owner:** evidence verifier. **Depends on:** F0, F1, F4, F5, F7, and F8 if applicable.

- [ ] Run focused publication, recovery, reader, Windows, alias, and exact stale-test validations.
- [ ] Run the full suite on the target Windows environment.
- [ ] Verify canonical paths/IDs/schemas/hashes/manifests/checkpoint identities are unchanged.
- [ ] Validate the entire final candidate and allowlist against immutable snapshot A: every admitted delta is within its recorded path/owner/reason, and every excluded or unlisted tracked/untracked production/code/config path remains identical by path, kind, bytes, mode/attributes, size, and SHA-256.
- [ ] Consume the B-before/B-after stale-test proof as the separate stale-maintenance result; do not substitute B for A in candidate authorization.
- [ ] Write `evidence/validation-manifest.yaml`; no evidence is written elsewhere.

**Gate:** all validation, A-bound admission authorization, B-only stale proof, and immutability checks pass.

### F10 — One final candidate

**Owner:** receipt controller. **Depends on:** F9.

- [ ] Freeze one exact path/byte/mode/attribute set and complete changed-path manifest.
- [ ] Write `evidence/final-candidate-manifest.yaml` with canonical and evidence hashes.
- [ ] Confirm no alternate candidate or post-freeze correction exists.

**Gate:** the candidate is immutable and reproducible.

### F11 — One native high-risk 4R receipt

**Owner:** receipt controller. **Depends on:** F10. **Not run by this package.**

- [ ] Route only the frozen candidate through one native review start.
- [ ] Use `review-risk`, `review-resilience`, `review-readability`, and `review-reliability`.
- [ ] Bind every lens to the same candidate and manifest.
- [ ] Treat any later path/byte/mode/evidence-scope change as receipt invalidation requiring explicit maintainer action.

**Gate:** one valid receipt covers the single final candidate.

## Current F5–F9 execution record

- [x] **F5 — Not applicable:** F1 revision 3 admits zero aliases; no alias path was changed or inferred.
- [x] **F6 — Not applicable:** no exact stale-test maintenance was established. The eight tests are F4 publication-contract maintenance, not narrow stale-test maintenance.
- [x] **F7 — Not applicable:** no snapshot-B comparison was performed because F6 does not apply; snapshot A remains the admission authority.
- [x] **F8 — RECORDED via a maintainer-approved lineage-gap exception and independent current-candidate re-attestation against immutable Snapshot A:** this `tasks.md` path remains P4's only prospective status surface. F1r3 exact bytes are unavailable; no r3→r4 preservation, byte-equivalence, or delta claim is made. Exact status semantics are `F8 recorded; F9 BLOCKED; F10/F11 ineligible`; `evidence/validation-manifest.yaml` remains F9 evidence only. No PASS, completion, real-run, publication, or native-receipt claim is made.
- [ ] **F9 — Blocked:** focused evidence is recorded, but the full pytest baseline remains `1517 passed, 12 failed, 1 skipped` and full Ruff has exactly two findings in `tests/test_prototype_loss.py`. See `evidence/validation-manifest.yaml` for exact commands, cache cleanup, attribution, and the no-cache strategy.
- [ ] **F10/F11 — Not eligible:** no final-candidate manifest is created and no receipt pass is claimed.

## Non-goals

No scientific change, new run, output/checkpoint/notebook mutation, historical rewrite, broad test repair, Git mutation, or multiple candidate/receipt is authorized.
