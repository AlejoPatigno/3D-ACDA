# Phase 18 — Acceptance Criteria

All criteria are **PENDING** because this action creates a blocked planning package, not an approved freeze. No criterion authorizes a real run.

## A. Scope and authorization

- [ ] **AC-18-001 — State boundary**  
  **Given** the Phase 18 OpenSpec state is read  
  **When** authorization fields are inspected  
  **Then** `phase_18_authorized=true`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` are present.

- [ ] **AC-18-002 — No runtime expansion**  
  **Given** the specification transaction completes  
  **When** owned paths are reconciled  
  **Then** no `src/`, `configs/`, `scripts/`, `tests/`, runtime output, manuscript, `.git/`, or unrelated dirty path has changed.

## B. Scientific resolution

- [ ] **AC-18-003 — Explicit value classes**  
  **Given** every numeric, categorical, or operational value in the package  
  **When** its evidence is reviewed  
  **Then** it is labeled `canonical_fixed`, `manually_selected_pre_run`, `engineering_only`, or `unresolved_blocking` and has a source or explicit missing-evidence reason.

- [ ] **AC-18-004 — Lambda discrepancy**  
  **Given** the primary `lambda_proto=1.0` evidence and later `lambda_proto=0.2` evidence  
  **When** the freeze is resolved  
  **Then** the publication value remains `unresolved_blocking` until an authoritative decision binds one value, the matrix compiler and real-run gate reject authorization while unresolved, and no target metric can select it.

- [ ] **AC-18-005 — Objective and checkpoint invariants**  
  **Given** a future run request  
  **When** its configuration is validated  
  **Then** warm/full equations, fixed epochs, source-validation macro-F1-only best selection, continuation after best save, and target-monitoring isolation are explicit and unchanged.

- [ ] **AC-18-006 — Inventory exclusions**  
  **Given** the runnable method inventory  
  **When** matrix rows are generated  
  **Then** only the seven protected methods appear, the publication ablation subset remains unresolved without human selection, and forbidden historical variants cannot become rows.

## C. Matrix and state

- [ ] **AC-18-007 — Complete dimensions**  
  **Given** an approved matrix  
  **When** its Cartesian product is materialized  
  **Then** it contains parser-bound canonical lowercase directions `adni_to_oasis` and `oasis_to_adni`, folds `0..4`, the explicit seed policy `[42]`, deterministic method order, and no selective-fold shortcut; display or uppercase aliases are rejected without remapping.

- [ ] **AC-18-008 — No completed rows**  
  **Given** the Phase 18 planning matrix  
  **When** every row state is inspected  
  **Then** each row is `PLANNED` or `BLOCKED`; no row is `COMPLETED`, training rows are distinct from checkpoint-projection rows, every projection has a valid `parent_training_id`, and there is exactly one training invocation per method/direction/fold/seed cell.

- [ ] **AC-18-009 — Failure and resume**  
  **Given** interruption, failure, corruption, or hash drift  
  **When** lifecycle state changes  
  **Then** the row remains visible, partial output is not promoted, resume requires identical identity hashes, and no silent retry, overwrite, or matrix omission occurs.

## D. Isolation and provenance

- [ ] **AC-18-010 — Target firewall**  
  **Given** a target-adaptation batch  
  **When** keys are validated  
  **Then** exactly `x`, `subject_id`, `subject_hash`, and `cohort` are accepted; labels and supervision/artifact fields are rejected before loss computation.

- [ ] **AC-18-011 — Assignment disjointness**  
  **Given** target adaptation and target evaluation manifests  
  **When** identity is checked  
  **Then** exact manifest bytes are hash-verified, parsed target-adaptation and target-evaluation subject identities have an empty intersection (aggregate hashes alone are insufficient), and target evaluation is labeled `MONITORING ONLY — NOT A TRAINING LOSS`.

- [ ] **AC-18-012 — Hash envelope**  
  **Given** a future real-run request  
  **When** provenance is validated  
  **Then** split, assignment, atlas/ROI, concept, Jacobian, model, config, environment, code, command, canonicalization-conformance, and authorization hashes are present and stable; missing or conflicting values fail closed. The checked-in CORAL/MMD/CDAN parameter ledger is validated and invented defaults are rejected.

## E. Feasibility and budget

- [ ] **AC-18-013 — Synthetic-only feasibility**  
  **Given** a feasibility invocation  
  **When** it runs before real authorization  
  **Then** it uses faithful synthetic tensor/data shapes only, exercises schema/firewall/checkpoint contracts, and produces no real-data or publication artifact; synthetic timing/resource observations remain engineering-only and cannot resolve real resource fields.

- [ ] **AC-18-014 — Honest resource budget**  
  **Given** no hardware observation is recorded  
  **When** the budget is read  
  **Then** conservative and nominal hardware, memory, storage, and wall-time values remain explicit unresolved placeholders rather than invented numbers.

## F. CLI, manuscript, and approval

- [ ] **AC-18-015 — Fail-closed CLI**  
  **Given** missing authorization, unresolved lambda, incomplete matrix, missing artifacts, or invalid hashes  
  **When** a future real command is requested  
  **Then** it stops before data loading and emits a structured reason.

- [ ] **AC-18-016 — Manuscript alignment**  
  **Given** repository evidence and no complete manuscript PDF  
  **When** alignment is audited  
  **Then** each item uses `MATCH`, `MANUSCRIPT_OUTDATED`, `REPOSITORY_OUTDATED`, or `UNRESOLVED`; ambiguous items remain unresolved and the manuscript is not rewritten.

- [ ] **AC-18-017 — Independent approval**  
  **Given** the complete artifact set  
  **When** independent review is performed  
  **Then** approval is recorded separately from this planning action; absent approval, OpenSpec remains blocked/planning and no implementation or real run begins.

## Evidence required for later transition

A later transition must provide the reviewed artifact hashes, resolved lambda decision, selected ablation subset, complete split/assignment/artifact manifests, hardware observations, resource approval, command hash, privacy/data authorization, independent review result, and explicit human real-run approval. Historical Phase 17 synthetic evidence alone is insufficient.
