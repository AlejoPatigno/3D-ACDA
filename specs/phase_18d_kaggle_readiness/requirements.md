# Phase 18D Kaggle Readiness Requirements

## Outcome

Phase 18D defines a Kaggle-only evidence pipeline that discovers the intended ADNI inputs, materializes privacy-preserving and hash-verifiable evidence, verifies the fixed OASIS policy, validates reusable Phase 4/concept/anatomy contracts, and imports readiness evidence into the repository. It does **not** train a model, perform real predictive evaluation, analyze publication outcomes, or execute Phase 19.

The current authority is `docs/PHASE18B_REPORT.md`, whose status remains `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`. The Phase 18D package does not supersede or mutate that authority.

## Scope and hard boundaries

- Source identity: `https://www.kaggle.com/datasets/sanjukaggling/adnidataset`.
- Kaggle dataset display name: `ADNI_dataset`.
- `ad_new_2_19_2026.csv` is a metadata candidate only; it becomes usable evidence only after runtime schema and SHA-256 verification.
- The mounted path is unresolved until discovered by contents inside the intended Kaggle runtime. No guessed mount path is permitted.
- Model-ready generation may occur in Kaggle using the approved Phase 4 preprocessing contract. Repository-side work may only import and validate its resulting evidence.
- No authorization flag may become true: `authorized`, `real_execution_authorized`, `freeze_approved`, and `publication_authorized` remain false; `phase_19_forbidden` remains true.

## Requirements

### R1. Standalone Kaggle notebooks and execution boundary

Provide three standalone notebooks with stable names and no hidden execution order:

1. `00_discover_kaggle_inputs.ipynb` discovers `/kaggle/input` by observed contents, identifies candidate metadata and source files, emits source/privacy evidence, and performs no training.
2. `01_materialize_kaggle_readiness.ipynb` performs resumable, hash-verified materialization, canonical subject/initial-MRI selection, approved Phase 4 preprocessing reuse, and deterministic source/target manifests. It may generate model-ready artifacts only inside Kaggle; it performs no model training or predictive evaluation.
3. `02_verify_kaggle_readiness.ipynb` verifies OASIS, cohort mappings, provenance, privacy, folds, target partitions, concept/anatomy reuse, and readiness-state transitions. It performs no training, predictive evaluation, publication analysis, or Phase 19 work.

Each notebook must be independently runnable after its declared inputs are available. A notebook must fail closed when a prerequisite is absent or ambiguous rather than infer a path, cohort, key, count, split, or authorization.

### R2. Dynamic input discovery

Discovery must enumerate contents below `/kaggle/input` and select inputs by observed names, file signatures, schemas, and source identity. It must not assume `/kaggle/input/ADNI_dataset`, any other fixed mount, a symlink, or a local repository path. It must record all candidate matches and the deterministic reason for selecting one; zero or multiple unresolved matches are blocking.

### R3. Exact provenance, hashes, and privacy outputs

The Kaggle evidence bundle must contain these canonical JSON outputs:

- `source_provenance.json`: source URL, observed Kaggle dataset name, discovery-relative paths, byte sizes, lowercase hexadecimal SHA-256 for every imported file, discovery timestamp, notebook identity/hash, and validation status.
- `metadata_manifest.json`: selected metadata relative path, exact file SHA-256, schema fingerprint, required-column result, row count, and candidate/approved disposition. It must not contain raw identifiers.
- `subject_artifacts.jsonl`: one row per canonical person and artifact, with HMAC-SHA256 subject token, HMAC key identifier/version, relative artifact path, byte size, artifact SHA-256, selected initial-MRI rule, and materialization status. The HMAC key is never emitted.
- `cohort_manifest.json`: binary label, source/target role, person token, artifact hashes, and manifest SHA-256; no raw subject ID, filename containing a raw ID, secret, or key.
- `splits_manifest.json`: source-fold membership, target-adaptation membership, target-evaluation membership, person-token disjointness proofs, target-firewall result, and manifest SHA-256.
- `privacy_report.json`: raw-ID scan result, secret/key scan result, filename/path privacy result, HMAC algorithm and key identifier/version, and explicit `raw_ids_emitted=false` and `secrets_emitted=false`.
- `readiness_state.json`: exact state, prerequisite statuses, evidence manifest hashes, authorization flags, and blocking reasons.

SHA-256 values must be computed over exact file bytes and encoded as lowercase 64-character hexadecimal strings. Evidence hashes must be recomputable by the repository validator. Timestamps and machine metadata must not be used as content identity.

### R4. Canonical ADNI mapping and person policy

The only accepted ADNI vocabulary is `CN`, `MCI`, and `AD`, mapped exactly as follows:

| ADNI source label | Binary label | ID |
|---|---|---:|
| `CN` | `CN` | 0 |
| `MCI` | `Impaired` | 1 |
| `AD` | `Impaired` | 1 |

Unknown, missing, malformed, duplicate, or conflicting assignments fail closed. The materialized cohort must contain one canonical person and one initial MRI per person. Longitudinal visits and later MRIs are excluded from the initial-MRI cohort; selection must use the approved Phase 4 metadata rule and recorded evidence, never an arbitrary fallback. A missing or ambiguous acquisition date/tie-breaker is blocking.

### R5. Approved preprocessing and reusable concept/anatomy contracts

Only the approved Phase 4 preprocessing contract may be reused. Phase 18D must record the exact contract identity/version and hashes of the reused outputs. It must not introduce a new normalization, spatial transform, ROI order, atlas, mask, Jacobian, or label-derived preprocessing variant.

Existing concept/anatomy artifacts may be reused only after read-only validation of their identities, shapes, ordering, hashes, and provenance against the approved contract. Label migration must not refit, regenerate, or reinterpret these artifacts. The existing `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian identities remain the compatibility surfaces identified by Phase 18B.

### R6. OASIS verification and mismatch behavior

Verify the supplied OASIS evidence against the closed structural policy:

- CDR domain `{0, 0.5, 1, 2}`;
- `0 -> CN`; positive observed values `0.5`, `1`, and `2 -> Impaired`;
- 436 visits, 416 canonical persons, and 20 longitudinal duplicate visits;
- 316 canonical CN persons and 100 canonical Impaired persons;
- fixed planning partitions of 332 target-adaptation persons and 84 target-evaluation persons;
- zero person intersection between target adaptation and target evaluation;
- person-level, not visit-level, split membership;
- conflicting person-level values are rejected;
- HMAC key identifier/version may be recorded, but the key is never recorded.

Any observed mapping, count, person policy, partition arithmetic, or intersection that does not match the approved evidence must produce `BLOCKED_COHORT_MISMATCH` and prevent readiness import. The verifier must not silently repair, downsample, remap, or replace OASIS evidence.

### R7. Splits and target firewall

Create deterministic source folds and fixed target adaptation/evaluation partitions from canonical person tokens. Every source fold must be person-disjoint. Target adaptation and target evaluation must be person-disjoint and equal the approved 332/84 planning partition when OASIS verification is active. No target evaluation identity, label, artifact, or derived statistic may enter adaptation inputs, source-fold construction, preprocessing fitting, checkpoint selection, or any training-like operation. Phase 18D performs no such operation; the firewall is an evidence contract for later work.

### R8. Resumable materialization

Materialization must be resumable at per-subject granularity. Each subject row must have a status such as `pending`, `materialized`, `reused_hash_verified`, `blocked`, or `failed`, an attempt-independent artifact hash, and a reason for non-success. Existing artifacts may be reused only when byte hashes, expected relative paths, contract identity, and privacy checks all match. Partial or corrupted artifacts must never be treated as complete, and recovery must not delete user-owned unrelated files.

### R9. Synthetic-only feasibility probes

Feasibility probes may use synthetic arrays or synthetic de-identified fixtures only. They may test discovery, hashing, resume/reuse, mapping, split arithmetic, privacy scanning, and schema validation. No subject data may be used for a probe, and no probe result may be reported as training, predictive evaluation, cohort evidence, or scientific performance.

### R10. Repository-side import validator and focused tests

Implement later, outside this planning action, a read-only `scripts/import_kaggle_readiness.py` validator. It must validate an already-produced evidence bundle, recompute hashes, enforce privacy and schema contracts, verify OASIS and split rules, reject target leakage, enforce the state machine, and emit no model-ready artifacts or authorization.

Focused tests must cover valid evidence, dynamic discovery without a guessed mount, hash mismatch, resume/reuse, raw-ID/secret rejection, mapping errors, `BLOCKED_COHORT_MISMATCH`, person overlap, target firewall violations, concept/anatomy regeneration attempts, forbidden training/publication/Phase 19 markers, and state transitions. Fixtures are synthetic only.

### R11. Readiness states and closure gate

The initial planning/execution state is `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION`. After successful evidence import, the only later state permitted by this change is `KAGGLE_READINESS_EVIDENCE_IMPORTED`. Neither state authorizes real training or evaluation. No artifact may emit or imply `REAL_RUN_READY`, `REAL_RUN_READY_FOR_EXECUTION`, or any equivalent authorization state.

Implementation closure requires the exact focused validation commands in `acceptance.md`, a clean independent review gate, and confirmation that all authorization flags remain false. A failed independent review leaves the change open or blocked; it cannot be bypassed by changing the state file.

## Non-goals

Real training, real predictive evaluation, publication analysis, model selection, model release, binary freeze approval, local ADNI mounting, repository-side model-ready generation, raw-ID import, secret import, repair of Engram, lifecycle receipt fabrication, and Phase 19 are forbidden.
