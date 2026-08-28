# Phase 18F — Post-Seed Validation Remediation Design

## Design decision

Use a narrow adapter around the existing concept-report output writer. It changes only bounded sibling naming, transaction provenance, and the supportable same-volume publication/recovery sequence. It does not change the canonical final path or content contract. Existing aliases remain a read/report projection concern.

The design deliberately does **not** promise an atomic directory exchange or continuous presence at the final path. A valid old tree is kept in an owned same-parent backup during the short two-rename publication window; cooperative readers follow the reader contract below.

```text
candidate tree -> manifest validation -> owned sibling + durable journal
                                      -> publisher lock
                                      -> final -> owned backup (same volume)
                                      -> validated sibling -> final
                                      -> final revalidation -> backup cleanup
```

## Candidate identity and admission

Before any implementation or test-maintenance write, the evidence verifier writes:

- `evidence/baseline-exclusion-manifest.yaml` — immutable snapshot A of protected/excluded paths and the complete relevant production/code/config baseline;
- `evidence/candidate-admission-manifest.yaml` — complete tracked and untracked production/code/config inventory and explicit candidate allowlist bound to A.

The admission inventory is not a `git diff src` check. It walks all designated production/code/config roots and joins tracked state, untracked state, kind, mode/attributes, size, and SHA-256. It records every path, including untracked paths that Git would not show in a normal tracked diff. Each path is `admitted`, `immutable`, or `blocked`, with an owner and reason. The allowlist names each new publication path, focused behavior-test path, pre-existing alias path, exact stale-test path when known, and pre-identified status path. A pre-existing alias path is admitted only with its A-bound baseline hash/mode and an explicit `pre_existing_alias` marker. Any unlisted or look-alike path is blocked.

Snapshot B is deliberately not captured at admission. After all authorized production and alias implementation and immediately before the exact stale-test edit, the stale maintainer captures B as the complete production/code/config projection in `evidence/stale-test-production-proof.yaml`. Immediately after the edit, B-after is recomputed. F7 compares only B-before with B-after for path, kind, mode/attributes, size, and SHA-256. B proves stale-test maintenance did not add production drift; it does not authorize candidate scope. Final candidate authorization separately validates the entire allowlist and all excluded/unlisted paths against immutable A.

## Publication identity and bounded name

The publication identity is deterministically serialized from existing values:

```yaml
publication_schema: <existing concept-output schema/version>
canonical_final_relative_path: <existing final path, unchanged>
canonical_method_id: <existing canonical internal ID>
canonical_config_hash: <existing hash>
artifact_hashes: <existing artifact hashes>
report_schema_hash: <existing report/schema hash>
```

Display aliases, absolute paths, timestamps, random values, and user labels are excluded from identity. The output-tree manifest includes every relative path, entry type, mode/attributes, byte length, and SHA-256, with no extra entries allowed.

The sibling grammar is:

```text
p3dco.<role>.<identity-token>.<attempt-token>[.c<collision-token>].tmp
```

The identity token is lowercase unpadded base32 over the canonical identity digest; its length is derived only after reserving the complete grammar. Attempt and collision tokens are lowercase base36. Every candidate is checked against the measured final path, sibling path, component, journal, and backup budgets before creating an entry.

## Durable transaction provenance

The publisher obtains a fixed minimum 32-byte capability from the OS CSPRNG. It requests the complete length, verifies the provider returned exactly that length, and stores/compares the complete encoded value; it never truncates, pads, or silently accepts a short read. A short read or unavailable CSPRNG is `BLOCKED` before mutation.

For each transaction it:

1. creates a journal with `CREATE_NEW`/equivalent in the final parent and same volume;
2. writes the complete capability and canonical identity, final relative path, schema/version, owner/attempt/collision tokens, expected manifest hash, same-volume file identifiers, mode/type expectations, and state;
3. durably flushes the journal according to the platform convention;
4. creates the sibling with exclusive creation and binds it to the journal/capability; and
5. durably records `prepared`, then `validated` only after complete-tree validation.

The journal state set is `prepared`, `validated`, `publishing`, `published`, and `aborted`. Recovery requires exact grammar, exact journal/capability, complete manifest, exact identity/path/schema/tokens, correct type/mode, same-volume evidence, and durable `validated`. A directory name or copied manifest alone is never provenance.

This is a normal stale-process recovery capability, not an assertion of cryptographic authentication against a foreign process with filesystem read/write/ACL authority. If an entry could be foreign, copied, replaced, ACL-altered, or otherwise cannot be distinguished from foreign activity, it is preserved and surfaced and recovery blocks. Unknown/look-alike siblings are never promoted or deleted. Exact provenance may authorize normal stale recovery only under that stated filesystem threat limitation.

## Supportable publication and reader semantics

The writer uses this sequence under an exclusive publisher lock:

1. preflight the final path, parent, volume, and budget;
2. create and populate the sibling; validate its complete manifest; flush it; write durable `validated`;
3. recheck final and sibling identities;
4. if a valid final exists, rename it to an authenticated same-parent backup using same-volume rename; otherwise continue with no backup;
5. write durable `publishing`, then rename the validated sibling to the final path;
6. revalidate the final tree and write durable `published`; and
7. remove only the authenticated backup after successful final validation.

The final path may be absent only between steps 4 and 5. The adapter measures this interval and enforces `T_absent_max`; a timeout returns `BLOCKED` and invokes conditional rollback. The bound applies while the process and filesystem are executing normally. A process crash, power loss, or arbitrary scheduler/filesystem failure can exceed a real-time bound, so the design makes no stronger guarantee.

If step 5 or final validation fails, the adapter attempts to rename the authenticated backup back to the final path. Successful rollback restores the old tree. Failed rollback preserves backup and candidate and returns `BLOCKED`; it does not claim the old tree remained continuously available and does not delete ambiguous entries.

Cooperating readers acquire the shared reader lock. During the publish interval they retry absence for the configured bounded retry window, then return structured `unavailable`; they never interpret absence as an empty output. Non-cooperating readers may observe old, absent, or new, but never a partial tree because each visible tree is independently complete. Readers never glob or inspect siblings/backups.

## Collision and recovery matrix

| Observation | Required action |
|---|---|
| Exact owned journal+sibling, complete, `validated`, final absent | Revalidate and promote; otherwise block |
| Exact owned sibling, final valid | Leave final untouched; preserve/schedule only authenticated cleanup |
| Wrong identity, manifest, capability, state, mode, type, volume, or journal | Preserve and surface; never adopt, overwrite, or delete |
| Foreign file/dir, symlink, junction, case variant, alternate suffix, look-alike | Preserve and surface; choose a bounded ordinal or block |
| `prepared` or incomplete owned transaction | Do not promote; abort only through exact authenticated policy |
| `publishing` after interruption | Revalidate both sides and journal; never guess |
| Invalid final plus ambiguous sibling | Preserve both and return `BLOCKED` |

A collision ordinal is selected only if the complete grammar still fits the derived budget. No broad cleanup is permitted.

## Alias boundary

The existing resolver receives stored canonical records and emits the existing report schema with requested spelling, canonical ID, display label, and existing resolution record. It does not write stored records or feed aliases into publication identity, hashes, paths, checkpoint identity, or manifests. An approved alias and canonical request must share identity while preserving request metadata; unknown, ambiguous, case-altered, and look-alike names fail closed.

## Dependency and evidence flow

Snapshot A and admission establish immutable candidate scope; snapshot B is intentionally later and is used only for stale-test maintenance. The acyclic flow is:

```text
snapshot A baseline exclusion
  -> A-bound candidate admission and allowlist
  -> path-budget/publication implementation
  -> publication behavior tests
  -> existing alias integration
  -> snapshot B immediately before exact stale-test maintenance (conditional)
  -> B-after projection and B-only proof
  -> prospective status decision and complete validation
       |-> final candidate authorization against A
  -> validation manifest
  -> final-candidate manifest
  -> one native high-risk 4R receipt
```

No edge points from F7/B to candidate admission or back to stale maintenance, so the graph remains acyclic. The four manifests and the stale-test proof are written only under this package's `evidence/` directory. `validation-manifest.yaml` binds A-bound candidate authorization, B-only stale proof, test results, admission comparison, reader/absence-window/rollback assertions, and protected-path comparisons. `final-candidate-manifest.yaml` freezes exact paths, bytes, modes/attributes, canonical hashes, and evidence hashes.

## Workload and review

The change is high risk because it controls publication, recovery, foreign-entry preservation, and a known Windows failure boundary. The final candidate receives exactly `review-risk`, `review-resilience`, `review-readability`, and `review-reliability` once. Intermediate work units are not final candidates or separate receipts. A candidate change after review start invalidates the receipt and requires explicit maintainer action.
