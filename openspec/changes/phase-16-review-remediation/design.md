# Phase 16 Review Remediation — Detailed Design

## Design decision

Implement the remediation as three serial boundaries around the existing concept-evaluation code:

1. **Slice A** makes candidate discovery and provenance validation strict when real evaluation is requested, while preserving the existing issue-reporting and fixture behavior for non-real callers.
2. **Slice B** adds an opaque, process-local real-evaluation capability and a single real orchestration preflight. The preflight verifies every canonical input before any model construction, inference, statistics, or publication. Checkpoints are inspected and loaded only through `weights_only=True` after file identity has been established.
3. **Slice C** makes output publication non-destructive by default. A valid existing result is never replaced when `overwrite=False`; a new result is either reused by identity or published to an atomically allocated deterministic version path. Explicit overwrite retains the current allowlist, backup, rollback, and manifest-last protections.

The design does not change metrics, aggregation, preprocessing, model architecture, datasets, GPU/network behavior, notebooks, the review lifecycle, incident `#1793`, or receipt `review-a81b3edbc82c5830`.

## Repository facts that constrain the design

- `scripts/evaluate_concepts.py::_execute` is the authoritative CLI mode boundary. Real `validate-only` and `evaluate` requests are currently blocked after checking the configured gate; the script has no existing real-data loader/statistics orchestration comparable to the synthetic path.
- `discovery.py` currently uses `torch.load(..., weights_only=False)` to inspect candidate metadata. `inference.py::load_checkpoint` does the same before constructing `PADA3DACB`.
- `ConceptCandidate` carries checkpoint and concept-artifact-root paths, but candidate atlas and normalizer claims are currently metadata-only. `compute_artifact_hashes` verifies the normalizer file but trusts `candidate.atlas_hash` instead of binding it to an atlas file.
- `inference.py::_canonical_roi_order_hash` returns `None` when labels are unavailable, which currently skips the runtime comparison. That behavior is retained only for explicitly fixture-only helpers; the real preflight treats missing labels as an error.
- `AtlasROIManager` already exposes the required compatibility surface: `atlas_path`, `atlas_hash`, `label_values`, `K`, `get_binary_masks()`, and `atlas_tensor`. Its constructor and method signatures remain unchanged.
- `ConceptNormalizer` persists `roi_labels` and can be loaded from JSON. Real validation will hash the file before parsing it and will require a non-empty label sequence.
- `report.commit_output` already stages a complete tree, writes `evaluation_manifest.json` last, and restores a backed-up tree after a failed replacement. Its missing behavior is the `overwrite=False` branch: it currently replaces an existing recognized tree regardless of the flag.
- Evaluation-level request errors use the sanitized exception types in `pada3dacb.evaluation.schemas`; concept package helpers currently use `pada3dacb.exceptions.ConfigurationError` or return issue lists. The design preserves those boundaries and does not add a parallel exception hierarchy.

## Cross-slice contracts

### 1. Real capability contract

A boolean, CLI flag, config field, environment variable, or direct function call is not a capability. The capability is a frozen, non-serializable value issued by one small factory in `evaluation/concepts/schemas.py`:

```text
RealEvaluationCapability
  schema_version: "phase16-real-evaluation-capability-v1"
  manifest_sha256: lowercase SHA-256 of the exact provenance-manifest bytes
  authorization_sha256: lowercase SHA-256 of canonical authorization evidence
  issuer: non-empty diagnostic label ("cli" or "trusted-programmatic")
  private issuer token: module-private object identity
```

The private token is checked by the real preflight; constructing a dataclass with the visible fields, passing `True`, or passing a string token is rejected. This is an accidental-bypass guard, not a claim of cryptographic isolation inside a trusted Python process.

The factory, named `issue_real_evaluation_capability`, accepts only:

- an authorization-evidence mapping with `authorized: true`;
- all four existing evidence entries (`authorized_exports`, `concept_normalizer`, `atlas_hash`, and `protocol_approval`) resolved to `true` with valid lowercase SHA-256 values;
- the exact manifest-byte SHA-256; and
- an issuer label.

The factory canonicalizes the evidence to derive `authorization_sha256`. It does not load a checkpoint, construct a model, or publish output.

**CLI path:** `_execute` reads the existing gate and the explicitly supplied canonical manifest, validates their syntax, then asks the factory for a capability. The default repository config remains unauthorized, so the current real gate remains closed. No new `--authorize` flag is introduced.

**Trusted programmatic path:** a caller obtains the same capability by calling the factory after assembling approved evidence and the manifest bytes, then passes the returned object as a keyword-only argument to the real orchestration function. Calling the orchestration function without it is always unauthorized; direct invocation is never authorization.

The capability is bound to the manifest digest and authorization digest. The real preflight compares both values before reading canonical artifact contents. It is not accepted as a substitute for file-hash verification.

### 2. Canonical provenance manifest

Slice A introduces a versioned, strict manifest model. The manifest is loaded from a caller-selected root, and all paths inside it are safe POSIX-relative paths below that root. Absolute paths, backslashes, `..`, missing files, duplicate candidate keys, unsupported schema versions, missing fields, and conflicting duplicate identities fail closed.

Canonical JSON shape:

```json
{
  "schema_version": "phase16-concept-provenance-v1",
  "roi_order": {
    "labels": [2, 4, 7],
    "sha256": "<sha256 of json.dumps(labels).encode('utf-8')>"
  },
  "atlas": {
    "relative_path": "atlas/atlas.nii.gz",
    "sha256": "<sha256 of the atlas file>",
    "roi_order_sha256": "<same value as roi_order.sha256>"
  },
  "candidates": [
    {
      "key": {
        "method_id": "source_only",
        "direction": "adni_to_oasis",
        "seed": 42,
        "fold": 0,
        "checkpoint_policy": "primary_best_source_f1"
      },
      "checkpoint": {
        "relative_path": "runs/checkpoints/source_only__adni_to_oasis__seed_42__fold_0/primary_best_source_f1/best_source_f1_epoch_50.pt",
        "sha256": "<sha256 of the checkpoint file>",
        "roi_order_sha256": "<same value as roi_order.sha256>"
      },
      "normalizer": {
        "relative_path": "artifacts/concept_normalizer.json",
        "sha256": "<sha256 of the normalizer file>",
        "roi_order_sha256": "<same value as roi_order.sha256>"
      },
      "concept_artifacts_root": "artifacts/concept_targets/adni_to_oasis/seed_42/fold_0"
    }
  ]
}
```

The exact candidate key is represented canonically by the five existing `ConceptCandidate.candidate_key` fields. The implementation may use a typed mapping internally, but serialized ordering and field names are fixed by the shape above.

Validation rules:

- every file hash is lowercase hexadecimal SHA-256;
- `roi_order.labels` is a non-empty list of unique integers, and its hash uses the established project algorithm (`json.dumps(labels).encode("utf-8")`), preserving order rather than sorting it;
- atlas, every normalizer, and every checkpoint entry carries the same ROI-order hash as the top-level record;
- all candidate keys requested by the real run have exactly one manifest entry, and no manifest entry is silently ignored;
- the atlas file hash is computed from the actual file and must equal the manifest and candidate/checkpoint claims;
- each normalizer file hash is computed from the actual file and must equal its entry and checkpoint claim; all normalizers participating in one run must have the same file hash and label sequence;
- each checkpoint path discovered by policy must equal its manifest assignment and its file hash must match before safe parsing;
- the parsed normalizer `roi_labels`, parsed atlas manager `label_values`, candidate metadata, checkpoint metadata, and runtime manager identity must all equal the same ordered labels/hash;
- missing labels are an error, not a reason to skip comparison;
- missing or conflicting fields produce actionable issue strings in discovery and a blocking configuration/provenance error at the real orchestration boundary.

The manifest binds file identity; it does not replace the existing target-file checks. The existing concept/anatomical target files remain checked by `compute_artifact_hashes` after their candidate artifact root has been assigned. No metric or target-generation policy changes.

### 3. Verified preflight result

Strict validation returns an immutable `VerifiedEvaluationInputs` value containing:

- the manifest digest and canonical ROI labels/hash;
- the verified atlas path, file hash, and labels;
- the verified normalizer paths, file hashes, and labels by candidate key;
- checkpoint `FileIdentity` values by candidate key; and
- the safe checkpoint metadata needed to validate candidate claims, without constructing a model.

The real execution path must receive this result. It must not re-derive eligibility from raw candidate fields or skip validation because a field is absent. Existing `discover_candidates` continues to return `(candidates, issues)` for discovery/reporting; the real boundary treats any actionable issue as blocking and does not load one candidate while another remains unverified.

## Exact real-run order

The order below is a contract and is covered by one event-order test with monkeypatched functions. No step may move earlier as an optimization.

1. **Request/config shape:** parse selectors and run mode; validate types, ranges, non-overlapping roots, approved methods/directions, and required runtime paths. This step has no model or checkpoint side effect.
2. **Capability authorization:** verify the capability's private issuer token, schema version, manifest digest, authorization digest, and real-mode binding. Missing, forged, stale, or mismatched capability raises `AuthorizationGateError` immediately.
3. **Manifest identity and canonical artifact verification:** read the exact manifest bytes, verify the capability-bound digest, parse the strict schema, resolve safe paths, then hash the actual atlas and normalizer files. Parse the normalizer only after its file hash matches. Construct `AtlasROIManager` only after the atlas file identity is established, then verify its `atlas_hash`, `label_values`, `K`, and masks against the manifest. No checkpoint is opened yet.
4. **Candidate assignment and checkpoint file identity:** discover the expected policy path, require an exact manifest assignment, open each checkpoint as a binary stream, compute its hash, and compare it with the manifest before parsing. All requested candidates are assigned and hashed before any model is built.
5. **Safe tensor-only checkpoint parsing:** seek the same verified stream and call `torch.load(..., map_location="cpu", weights_only=True)`. Require a top-level mapping, tensor-only `model_state_dict` (or the explicitly supported legacy `model` state-dict key), primitive metadata, and a mapping configuration. Validate checkpoint experiment/model/training hashes, atlas hash, normalizer hash, ROI-order hash, policy, and epoch against the candidate and manifest. A load failure is reported as unsupported/unsafe checkpoint format; there is no `weights_only=False` fallback.
6. **Model construction:** only after the complete preflight and safe checkpoint inspection succeed, construct `PADA3DACB` from the validated primitive config and load the verified state dict strictly. An incompatible state dict is a configuration error; it is never retried with a different loader or architecture.
7. **Inference:** construct the approved local dataloader, enforce the runtime atlas/normalizer/ROI contract, and call the existing no-grad `run_subject_inference`. The batch mask checks remain in place. The runtime strict path requires labels; the existing label-less fixture compatibility is available only when the caller explicitly selects synthetic/fixture mode.
8. **Statistics:** pass already-materialized records to the existing aggregation, metric, bootstrap, stability, and agreement helpers. These standalone helpers do not gain a capability parameter and remain usable for unit tests and already-materialized data. The capability gates the orchestration boundary, not pure statistics.
9. **Publication:** build all ordinary artifacts and the completion manifest in memory, allocate the output destination, write the stage with the completion manifest last, and atomically publish it. No result path is made visible as complete before the manifest commit.

The real boundary should be a small `run_real_evaluation(..., capability=..., verified_inputs=...)`/preflight wrapper used by the CLI and trusted callers. `run_subject_inference`, metric helpers, and synthetic fixture builders remain lower-level APIs. Any call to the candidate orchestration with `analysis_mode=REAL` and no capability fails before `load_checkpoint`, model construction, forward, statistics, or writer invocation.

## Compatibility rules

### Existing `AtlasROIManager` APIs

Do not change `AtlasROIManager.__init__`, `get_binary_masks`, `get_masks`, `label_values`, `atlas_hash`, or `K`. Real validation uses the existing manager and compares its derived values with the manifest. The inference helper continues to support managers exposing either `get_binary_masks()` or the existing `atlas_tensor` fallback, and continues to support an optional target shape. The strict real preflight rejects a manager that lacks a usable ordered label sequence rather than weakening the comparison.

### Synthetic fixtures and validate-only mode

- `analysis_mode=synthetic_test_only` remains explicitly fixture-only. It does not require a real capability or canonical real manifest, and it cannot satisfy the real preflight.
- Existing `validate-only` synthetic behavior still constructs the deterministic CPU fixture model, skips statistics, and writes nothing.
- Existing synthetic report generation remains deterministic. A first publication to an absent output path may continue to use that requested path; the non-destructive version branch is exercised when a recognized result already occupies the requested path.
- The current test doubles that expose only `K` and `get_binary_masks()` remain valid in fixture mode. They are not accepted by strict real validation unless they also expose the required ordered labels and atlas identity.

### Legacy checkpoints

Legacy checkpoints are supported only when they can be read by the safe tensor-only loader and contain the explicitly supported state-dict/config shape. Missing real provenance fields, missing ROI labels, arbitrary custom objects, and formats that require pickle object reconstruction are rejected. There is no compatibility fallback to `weights_only=False`; migration of such checkpoints is outside this change. Synthetic unit fixtures may continue using minimal metadata because they do not enter the real boundary.

### Configuration normalization

The canonical real gate key is the existing repository key `real_evaluation_gate`. `ConceptEvaluationConfig.from_yaml` currently expects `real_gate`, which is inconsistent with `configs/evaluation/concepts.yaml`; Slice A should correct that parser and validate the actual key. The implementation should not silently accept an ambiguous legacy key for real mode. The default config remains `authorized: false` with unresolved evidence, preserving the current closed state.

Minimum strict configuration validation covers:

- mapping shape and required schema/protocol versions;
- non-empty, duplicate-free methods, directions, policies, folds, seeds, and top-k values;
- integer/range checks for folds, seeds, bootstrap replicates, bootstrap seed, and batch size;
- exact class order and direction/method enum membership;
- real-mode manifest path, atlas path/assignment, normalizer assignments, expected hashes, device, and output roots;
- no input/output root overlap; and
- consistency between configured expected hashes and manifest/file hashes.

No scientific threshold, metric, aggregation, or cohort policy is introduced.

## Slice ownership and serial dependency graph

Each slice is one review unit with a forecast below the 400-authored-line budget, including focused tests and active evidence. Slices are not parallel edits.

### Slice A — candidate provenance and configuration eligibility

**Owned production files**

- `src/pada3dacb/evaluation/concepts/schemas.py`: strict manifest/file-identity value objects, hash/path validation, and strict configuration normalization. Preserve loose dataclass construction needed by existing fixture tests; strict validation happens at the real eligibility boundary.
- `src/pada3dacb/evaluation/concepts/provenance.py`: manifest parsing, canonical ROI-order hashing, actual atlas/normalizer/checkpoint identity checks, safe checkpoint metadata inspection, and cross-artifact consistency checks. Keep `compute_sha256_*` helpers and `compute_artifact_hashes` usable for existing materialized artifacts.
- `src/pada3dacb/evaluation/concepts/discovery.py`: validate `DiscoveryConfig`, remove `weights_only=False`, require exact manifest assignment in strict mode, and retain issue-list discovery/exclusion behavior in non-strict mode.

**Owned tests**

- `tests/test_concept_provenance.py`
- `tests/test_concept_discovery.py`
- the smallest configuration/schema test file already used by the repository (otherwise add focused cases to `tests/test_concept_discovery.py`; do not create a broad schema suite).

**Dependency output**

A strict discovery request yields candidates plus a complete `VerifiedEvaluationInputs` preflight input. It must be possible for Slice B to reject before model construction without re-reading unverified candidate claims.

**Budget forecast:** approximately 220 production/test lines, with a hard stop before 400 authored lines.

### Slice B — authorization and safe checkpoint/model execution

**Owned production files**

- `src/pada3dacb/evaluation/concepts/schemas.py`: add the opaque capability contract and issuer factory after Slice A is complete.
- `src/pada3dacb/evaluation/concepts/inference.py`: safe stream identity/hash, `weights_only=True` inspection/loading, strict real-mode orchestration gate, and runtime ROI contract. Keep fixture-compatible low-level calls explicit rather than using them as real authorization.
- `scripts/evaluate_concepts.py`: add the smallest manifest/capability handoff to the authoritative `_execute` path and route real requests through the preflight boundary. Do not add a dataset loader, network access, GPU path, notebook, or Phase 17 behavior.

**Owned tests**

- `tests/test_concept_inference.py`
- `tests/test_concept_modes.py`
- `tests/test_concept_cli.py` only for the capability/manifest handoff and unauthorized direct-call regression.

**Dependency input:** Slice A's strict manifest and verified identity contracts.

**Budget forecast:** approximately 260 production/test lines, with a hard stop before 400 authored lines.

**Repository integration constraint:** the current CLI contains no real-data loader/statistics pipeline. The implementation must expose the real orchestration seam through dependency injection or existing approved local callbacks; it must not invent a data source. If no approved local callback exists, the CLI remains closed with an actionable configuration error rather than silently treating synthetic fixtures as real. This is an integration gap to resolve during implementation, not a scientific decision.

### Slice C — deterministic publication and truthful evidence

**Owned production files**

- `src/pada3dacb/evaluation/concepts/report.py`: non-destructive allocation, valid-output identity reuse, reservation/lock handling, generic completed-tree verification, and preserved overwrite rollback.
- `tests/test_concept_report.py`: publication and failure tests.
- `openspec/changes/phase-16-review-remediation/remediation-evidence.md`: a short truthful evidence record only; do not edit incident or review-receipt artifacts.

**Dependency input:** Slice B returns the actual published `Path` and has no publication before preflight/inference/statistics complete.

**Budget forecast:** approximately 280 production/test/evidence lines, with a hard stop before 400 authored lines.

## Slice C publication contract in detail

### Destination identity and version format

`output_root` remains the stable requested path. With `overwrite=False`:

1. If `output_root` is absent, publish the first valid result at `output_root`, preserving current first-run caller ergonomics.
2. If `output_root` is a valid completed result and its manifest has the same `evaluation_identity`, return that path without rewriting any byte.
3. If `output_root` is a different valid completed result, preserve it and allocate the first free deterministic sibling `output_root.v000001`, then `output_root.v000002`, and so on. The returned `Path` is the path consumers must use.
4. If `output_root` exists but is invalid, contains unknown entries, is not a directory, or has an unreadable/conflicting manifest, fail without modifying it. Do not use an invalid tree as an overwrite target.
5. Existing version siblings are never replaced under `overwrite=False`; an occupied or invalid sibling is skipped and preserved.

The identity match is the completion-manifest `evaluation_identity`, not wall-clock time. This resolves the repeated-run/concurrent-run requirement: a completed sequential repeat is idempotently reused, while attempts that reserve destinations concurrently receive distinct version slots.

### Concurrency and atomicity

Use a small cross-platform allocation lock represented by an atomically-created directory under the output parent. Under that lock, reserve the selected destination with a tokenized hidden reservation entry before the expensive stage write. The reservation is removed in `finally`; the destination itself remains absent until the complete stage is atomically renamed into place. A second active attempt skips the reservation and receives the next version. A completed identity discovered after a sequential retry is reused.

Stage files live beside the destination with a tokenized hidden name. Each file is written and flushed; all ordinary artifacts and `artifact_index.json` are written before `evaluation_manifest.json`. The entire stage is then published with `os.replace`/the existing injected `replace` function. No partial tree is presented as complete because the manifest is both last in the stage and the completion marker.

Controlled failure removes the stage and reservation. If an overwrite transaction has already moved the old tree to backup, the existing restoration path is retained and tested. Incomplete hidden reservation/stage pairs left by process termination are recognizable by their token and may be reclaimed only by the allocator under the same lock; an incomplete destination without a manifest is never treated as a valid result. No arbitrary user directory is deleted during cleanup.

### Allowlist and verification

Retain the exact artifact-key check before staging. Strengthen existing-tree inspection to account for all entries, not only files, and reject unexpected files, directories, or symlinks for overwrite. Generic completed-tree verification checks the manifest's identity, output hashes, exact ordinary file set, artifact-index bytes, and manifest schema. The existing synthetic reuse behavior remains available through an `expected_analysis_mode` argument/default; real completed trees may be recognized for non-overwrite preservation without changing metric semantics.

## Focused test matrix and evidence

### Slice A tests

- valid manifest with actual atlas/normalizer/checkpoint hashes produces one eligible candidate;
- missing, malformed, uppercase, or mismatched file hashes exclude the candidate;
- missing files, unsafe paths, duplicate keys, missing manifest entries, and conflicting assignments fail closed;
- atlas labels, normalizer labels, candidate metadata, and checkpoint metadata agree exactly; missing labels and reordered labels are blocking;
- invalid config types, negative/non-integer ranges, duplicate selectors, missing real paths, and expected-hash conflicts are rejected;
- non-strict fixture discovery still returns issue lists and preserves not-applicable method behavior;
- a discovery spy proves checkpoint inspection uses `weights_only=True` and hashes the file before parsing.

### Slice B tests

- no capability, a forged visible-field object, a stale manifest digest, or incomplete gate evidence fails before `torch.load`, `PADA3DACB`, forward, statistics, or writer calls;
- CLI authorization creates the capability only after canonical manifest/gate checks; direct programmatic real calls must pass the capability explicitly;
- event-order assertions cover `authorize < artifact_hash < checkpoint_hash < safe_load < model_ctor < forward < statistics < publish`;
- `torch.load` is observed with `weights_only=True`; a checkpoint requiring arbitrary object reconstruction raises a clear unsupported-format error and is never retried unsafely;
- all candidate checkpoints are preflighted before the first model is constructed;
- actual `AtlasROIManager` labels/hash and a fixture manager using the existing `get_binary_masks()` API both retain their intended behavior; label-less fixtures are accepted only outside strict real mode;
- existing synthetic deterministic, validate-only, dry-run, and no-output tests continue to pass;
- standalone metric/statistics helpers remain callable on materialized records without a capability.

### Slice C tests

- first publication to an absent path remains deterministic;
- an existing valid output is byte-for-byte unchanged when `overwrite=False`;
- a different identity is published at `output.v000001` (or the next deterministic free slot), and the returned path is the version path;
- sequential identical retries reuse the completed identity without rewriting it;
- two controlled concurrent attempts reserve different slots, with no collision, duplicate version, partial destination, or leaked stage/reservation after completion;
- invalid/unknown existing trees are never replaced under either non-overwrite or overwrite rules;
- injected writer/replace failures restore the prior allowlisted tree and remove controlled temporary state;
- write-order spy proves `evaluation_manifest.json` is last;
- manifest/artifact-index tampering is rejected by completed-tree verification.

### Truthful evidence artifact

`remediation-evidence.md` records only:

- the focused commands and their actual result/count;
- lint, `py_compile`, and `git diff --check` results for the remediation paths;
- the prior full-suite timeout as **incomplete evidence**, not a pass;
- the exact statement that incident `#1793` and receipt `review-a81b3edbc82c5830` remain escalated and unchanged; and
- a scope statement that no real cohort, network, GPU, notebook, Phase 17, or review-lifecycle operation was performed.

It must not copy “complete”, “approved”, “cleared”, or “full suite passed” wording from any inconsistent prior task artifact.

## Rollout, rollback, and review boundary

1. Apply Slice A and run only its focused tests plus the required static checks. Real evaluation remains closed by the unchanged default gate.
2. After Slice A evidence is reviewable, apply Slice B. Verify unauthorized and load-order behavior before any real callback can be wired. Keep the real CLI closed when the repository lacks an approved local orchestration dependency.
3. After Slice B evidence is reviewable, apply Slice C. Verify publication preservation, allocation, rollback, and evidence wording.
4. If a slice fails, revert only that slice's code, tests, and newly created evidence. Keep prior valid output trees, incident state, and receipt state untouched. Never restore `weights_only=False` as a rollback strategy.
5. No review start/finalize/validate/archive or other lifecycle command is part of this design. Native incident `#1793` and escalated receipt `review-a81b3edbc82c5830` remain immutable.

## Risks and unresolved implementation choices

- **Real orchestration dependency is absent from the focused repository surface.** The design deliberately defines a dependency-injected seam instead of inventing data loading or touching public datasets. Implementation must identify an already-approved local callback or keep the real CLI blocked. This is the only delivery integration choice not resolvable from the inspected files.
- **Capability trust is process-local.** The opaque token prevents accidental construction and missing-argument bypasses, but Python callers in the same process are trusted by product definition. No network token service or lifecycle change is introduced.
- **Output allocation recovery after process termination needs a bounded implementation test.** The selected reservation-token design makes normal success/failure leak-free and permits safe cleanup of recognizable incomplete reservations under the allocation lock. The implementation must not use time-based guessing to delete an active reservation; if ownership cannot be proven, it must fail closed and leave the prior valid result untouched.
- **Legacy safe-load support is intentionally narrow.** A checkpoint that cannot be parsed with `weights_only=True` is rejected rather than migrated implicitly. Any migration policy is a separate change.
- **The specification's sequential-idempotence and concurrent-distinctness cases are reconciled by reserving before staging and reusing only completed matching identities.** If implementation tests cannot reliably distinguish active reservations, stop and surface the conflict instead of weakening either guarantee.
