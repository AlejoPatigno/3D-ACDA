# Experiment Freeze Contract

## ADDED Requirements

### Requirement: Phase 18 remains planning-only until independently approved

The change MUST preserve `phase_18_authorized: true`, `real_execution_authorized: false`, `publication_authorized: false`, and `phase_19_forbidden: true` until a separate human decision and independent specification approval are recorded.

#### Scenario: Read blocked OpenSpec state

- **GIVEN** the Phase 18 state is read before scientific approval
- **WHEN** authorization fields are inspected
- **THEN** the state is `blocked`/planning and real execution, publication, and Phase 19 remain forbidden.

#### Scenario: Attempt unauthorized real execution

- **GIVEN** any unresolved blocker or false real-run authorization
- **WHEN** a future runtime or CLI requests ADNI/OASIS access
- **THEN** it fails before data loading and records a structured blocked reason.

### Requirement: The scientific inventory and matrix are deterministic

The freeze MUST contain exactly the protected seven-method inventory, parser-bound canonical lowercase direction IDs `adni_to_oasis` and `oasis_to_adni`, folds `0..4`, the explicit repository seed policy `[42]`, fixed class order `CN=0,MCI=1,AD=2`, and separate `best_source_f1`/`last` checkpoint policies. Display or uppercase direction aliases MUST be rejected rather than silently remapped. Historical selective-fold behavior and unapproved method identities MUST NOT create matrix rows.

#### Scenario: Materialize the primary matrix

- **GIVEN** an approved matrix definition
- **WHEN** rows are generated
- **THEN** there are 70 training rows and 70 checkpoint-projection rows, exactly one training invocation per method/direction/fold/seed cell, each projection has `row_kind: checkpoint_projection` and a valid `parent_training_id`, order is deterministic, and no row is omitted, duplicated, or orphaned.

#### Scenario: Inspect planning states

- **GIVEN** the Phase 18 planning matrix
- **WHEN** row states are inspected
- **THEN** rows are `PLANNED` or `BLOCKED`; no row is `COMPLETED`.

### Requirement: Scientific values are explicit and unresolved values fail closed

Every value MUST be classified as `canonical_fixed`, `manually_selected_pre_run`, `engineering_only`, or `unresolved_blocking`. The `lambda_proto=0.2` versus `1.0` conflict MUST remain unresolved until authoritative evidence binds a value; the matrix compiler and real-run gate MUST reject authorization while unresolved; target outcomes MUST NOT resolve it. Checked-in CORAL adaptation weight, MMD weight/kernel/bandwidths, and CDAN weight/GRL/discriminator settings are mandatory `unresolved_blocking` fields until authoritative configs and loader validation exist; invented defaults are forbidden. Publication ablation inclusion MUST remain unresolved until human selection.

#### Scenario: Missing scientific resolution

- **GIVEN** the lambda conflict or publication ablation selection is unresolved
- **WHEN** a real-run identity is requested
- **THEN** resolution fails with a scientific blocker and no data path is opened.

### Requirement: Training and target-isolation invariants are preserved

The future runtime contract MUST use fixed epochs, no early stopping, source-validation macro-F1-only best-checkpoint selection, continued training after a best save, and target monitoring that cannot influence training or selection. Target adaptation and evaluation MUST be disjoint by a content-level intersection over hash-verified manifest contents; aggregate assignment hashes alone are insufficient. Adaptation batches MUST contain exactly `x`, `subject_id`, `subject_hash`, and `cohort`.

#### Scenario: Validate target adaptation

- **GIVEN** a target-adaptation batch with an extra diagnosis, probability, concept, Jacobian, or supervision field
- **WHEN** the batch is validated
- **THEN** validation fails before loss computation rather than dropping the field.

#### Scenario: Validate target monitoring

- **GIVEN** target evaluation metrics
- **WHEN** they are recorded
- **THEN** they carry `MONITORING ONLY — NOT A TRAINING LOSS` and cannot select a checkpoint, epoch, method, seed, fold, or hyperparameter.

### Requirement: Provenance and hashes are immutable

A future run MUST bind split/assignment, atlas/ROI, concept/Jacobian, model/configuration, code/environment, command, privacy, budget, review, canonicalization conformance, and authorization hashes. Structured hashes MUST use the versioned `phase18.canonical-json.v1` profile with deterministic numeric, negative-zero, Unicode, and separator rules and authoritative conformance vectors; exact files MUST use exact-byte SHA-256. Missing vectors, conflicting, remapped, regenerated, or drifted identities MUST fail closed.

#### Scenario: Resume an interrupted cell

- **GIVEN** a checkpoint and all identity hashes match exactly
- **WHEN** resume is requested for the same method, direction, fold, seed, and configuration
- **THEN** resume may continue without duplicate history rows.

#### Scenario: Resume with identity drift

- **GIVEN** any changed coefficient, assignment, artifact, command, or hash
- **WHEN** resume is requested
- **THEN** it fails without overwriting the existing identity.

### Requirement: Feasibility is synthetic-only and budget values are honest

Feasibility MUST use faithful synthetic shapes and schemas only. It may validate shapes/contracts but MUST NOT resolve real wall-time or resource fields. Hardware, memory, storage, duration, worker, and retry values without real observations MUST remain unresolved placeholders. Synthetic results MUST NOT be presented as real performance or publication evidence.

#### Scenario: Run synthetic feasibility

- **GIVEN** the real gate is closed
- **WHEN** feasibility is requested
- **THEN** only synthetic data is used, contract observations are recorded, and no real-data or publication artifact is produced.

### Requirement: Manuscript alignment is audited without rewriting

The audit MUST classify comparisons as `MATCH`, `MANUSCRIPT_OUTDATED`, `REPOSITORY_OUTDATED`, or `UNRESOLVED`. Missing complete manuscript evidence MUST preserve unresolved status; this change MUST NOT rewrite manuscript content.

#### Scenario: Audit unavailable manuscript source

- **GIVEN** no complete manuscript PDF exists
- **WHEN** alignment is evaluated
- **THEN** unsupported discrepancies remain `UNRESOLVED` and no manuscript file is modified.
