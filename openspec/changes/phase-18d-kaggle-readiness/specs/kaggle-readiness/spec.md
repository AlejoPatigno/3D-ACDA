# Kaggle Readiness Specification

## Requirements

### Requirement: Three standalone no-training notebooks
The change MUST define standalone Kaggle notebooks `00_discover_kaggle_inputs.ipynb`, `01_materialize_kaggle_readiness.ipynb`, and `02_verify_kaggle_readiness.ipynb`. Each MUST declare inputs and outputs and MUST NOT train a model, run real predictive evaluation, perform publication analysis, or execute Phase 19. Model-ready generation MAY occur only inside Kaggle under the approved Phase 4 contract; repository-side work MUST import evidence only.

#### Scenario: Notebook boundary is inspected
- **WHEN** the notebook contracts are validated
- **THEN** all three names and their no-training boundaries are present
- **AND** no training, evaluation, publication, or Phase 19 action is authorized

### Requirement: Dynamic Kaggle discovery
The discovery notebook MUST enumerate contents recursively below `/kaggle/input` and select candidates by observed contents, schema, and source identity. It MUST NOT assume a mount path such as `/kaggle/input/ADNI_dataset`.

#### Scenario: Candidate path differs between runtimes
- **WHEN** the same valid content is placed under different synthetic mount layouts
- **THEN** discovery selects by content and produces equivalent source identity evidence
- **AND** a guessed path is not required

#### Scenario: Candidate is absent or ambiguous
- **WHEN** zero or multiple candidates match `ad_new_2_19_2026.csv` and its required schema
- **THEN** discovery fails closed with a blocking reason
- **AND** it does not choose by path order

### Requirement: Exact provenance and privacy evidence
The evidence bundle MUST contain `source_provenance.json`, `metadata_manifest.json`, `subject_artifacts.jsonl`, `cohort_manifest.json`, `splits_manifest.json`, `privacy_report.json`, `concept_anatomy_reuse.json`, and `readiness_state.json`. Every declared SHA-256 MUST be computed from exact bytes and encoded as lowercase 64-character hexadecimal. Evidence MUST contain no raw IDs, raw-ID filenames, secrets, or HMAC keys; it MAY contain HMAC algorithm and key ID/version.
The repository importer recomputes SHA-256 only for files physically present in the exported bundle. For absent raw source CSV/MRI bytes, it validates the Kaggle-attested external content hash fields but never claims to recompute absent bytes.

#### Scenario: Evidence is imported
- **WHEN** the read-only importer validates a complete bundle
- **THEN** it recomputes every declared hash for files physically present in the bundle and validates the Kaggle-attested external content hash fields for absent raw source CSV/MRI bytes without recomputation
- **AND** it does not write or generate model-ready artifacts

#### Scenario: Raw ID or secret is found
- **WHEN** any canonical evidence, notebook output, path, or metadata contains a raw ID, secret, or HMAC key
- **THEN** validation fails closed
- **AND** readiness is not imported

### Requirement: Canonical ADNI mapping and person policy
The accepted ADNI vocabulary MUST be exactly `CN`, `MCI`, and `AD`, mapping `CN -> CN=0`, `MCI -> Impaired=1`, and `AD -> Impaired=1`. Materialization MUST retain one canonical person and one initial MRI per person under the approved Phase 4 selection rule. Unsupported, missing, duplicate, conflicting, or ambiguous assignments MUST block.

#### Scenario: Valid ADNI labels are mapped
- **WHEN** a row has one of the three accepted labels
- **THEN** it receives the fixed binary label and ID
- **AND** no label migration changes concept/anatomy artifacts

#### Scenario: Person has multiple visits or ambiguous initial MRI
- **WHEN** longitudinal visits exist or the initial selection cannot be proven
- **THEN** later/duplicate visits are excluded under the recorded rule
- **AND** missing/ambiguous selection blocks rather than guessing

### Requirement: Approved preprocessing and concept/anatomy reuse
The pipeline MUST reuse only the approved Phase 4 preprocessing contract. It MUST validate, without mutation, existing `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian identities. Label migration MUST NOT refit or regenerate these artifacts.

#### Scenario: Reuse is hash and identity verified
- **WHEN** existing artifacts match the approved contract, shape, ordering, and hashes
- **THEN** the reuse evidence passes
- **AND** no refit or regeneration runs

#### Scenario: Label migration attempts regeneration
- **WHEN** a bundle contains a new fit or regenerated concept/anatomy artifact attributed to label migration
- **THEN** validation blocks the bundle
- **AND** the state does not advance

### Requirement: OASIS verification and mismatch state
The verifier MUST enforce the approved OASIS policy: CDR `{0, 0.5, 1, 2}`, `0 -> CN`, positive values -> `Impaired`, 436 visits, 416 canonical persons, 20 longitudinal duplicates, 316 CN and 100 Impaired persons, 332 adaptation and 84 evaluation persons, zero adaptation/evaluation intersection, person-level splits, and rejection of conflicting person-level values. HMAC key material MUST remain secret.

#### Scenario: OASIS matches the approved policy
- **WHEN** all mappings, counts, person rules, partitions, and intersections match
- **THEN** verification passes the OASIS gate
- **AND** only a key ID/version, never the key, is retained

#### Scenario: OASIS differs from approved evidence
- **WHEN** any OASIS mapping, count, person policy, partition, or intersection differs
- **THEN** the verifier emits exactly `BLOCKED_COHORT_MISMATCH`
- **AND** it does not repair, remap, replace, or import the evidence

### Requirement: Person-level folds, partitions, and target firewall
The pipeline MUST create deterministic source folds from person tokens and fixed target adaptation/evaluation partitions of 332 and 84 people with zero overlap. Target-evaluation identities and derived data MUST be excluded from adaptation, source folds, preprocessing-fit inputs, and checkpoint selection.

#### Scenario: Person sets are disjoint
- **WHEN** split manifests are verified
- **THEN** source folds are disjoint and target adaptation/evaluation intersection is empty
- **AND** the manifest includes an explicit intersection proof

#### Scenario: Target firewall is violated
- **WHEN** a target-evaluation token or derived value appears in adaptation or source-fold inputs
- **THEN** validation blocks with a target-firewall failure
- **AND** no training or evaluation is run to conceal the violation

### Requirement: Resumable materialization
Materialization MUST expose per-subject statuses and MUST reuse an existing artifact only after exact hash, path, contract, and privacy verification. Corrupt or mismatched artifacts MUST be blocked or failed and MUST NOT be overwritten silently.

#### Scenario: Verified artifact already exists
- **WHEN** all reuse checks pass
- **THEN** status is `reused_hash_verified`
- **AND** the artifact bytes remain unchanged

#### Scenario: Artifact hash differs
- **WHEN** a prior artifact does not match its declared hash
- **THEN** status is `blocked` or `failed` with a reason
- **AND** the mismatch is not accepted as materialized

### Requirement: Synthetic-only feasibility probes
Feasibility probes MUST use synthetic arrays or synthetic de-identified fixtures only. They MUST NOT train on subjects or report subject-derived performance.

#### Scenario: Probe runs
- **WHEN** a focused feasibility test executes
- **THEN** it exercises contracts only with synthetic data
- **AND** it cannot produce training, evaluation, publication, or authorization evidence

### Requirement: Read-only importer and focused tests
The repository MUST later contain a read-only `scripts/import_kaggle_readiness.py` validator and focused synthetic tests. The validator MUST validate explicit evidence-root input, schemas, exact hashes, privacy, mappings, OASIS, splits, reuse, forbidden actions, and state without generating model-ready artifacts or changing authorization.

#### Scenario: Valid bundle reaches import state
- **WHEN** all required checks and independent review evidence pass
- **THEN** state may advance from `KAGGLE_READINESS_EVIDENCE_PRODUCED` to `KAGGLE_READINESS_EVIDENCE_IMPORTED`
- **AND** all authorization flags remain false

### Requirement: Readiness states and closure review
Only `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION`, `KAGGLE_READINESS_EVIDENCE_PRODUCED`, and `KAGGLE_READINESS_EVIDENCE_IMPORTED` MUST be valid states. Any `REAL_RUN_READY*` state MUST be rejected. Implementation closure MUST require the exact validation commands and an independent review PASS.

#### Scenario: Forbidden state is supplied
- **WHEN** a bundle supplies `REAL_RUN_READY` or an equivalent state
- **THEN** validation fails closed
- **AND** Phase 19 remains forbidden

#### Scenario: Independent review fails
- **WHEN** the independent reviewer reports a blocking finding
- **THEN** closure is blocked
- **AND** no state or authorization field is edited to bypass the finding