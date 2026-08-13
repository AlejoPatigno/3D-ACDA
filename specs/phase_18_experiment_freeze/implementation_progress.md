# Phase 18 Work Unit 1 Implementation Progress

## Status consumed

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: apply
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
warnings:
  - Planning state remains scientifically blocked.
  - No authorization fields were changed.
  - Existing unrelated dirty paths were preserved.
```

## Work unit

**Work Unit 1 — canonical JSON identity plus strict typed freeze/schema primitives.**

Start state: no `publication` package. End state: isolated CPU-only canonicalization and schema primitives with no loaders, runner, feasibility execution, resource measurement, publication metrics, real-run CLI, or Phase 19 behavior.

## Completed behavior

- Added the `phase18.canonical-json.v1` UTF-8, no-trailing-newline serializer.
- NFC-normalized strings and mapping keys with normalization-collision rejection.
- Preserved list/tuple order, sorted mapping keys, emitted deterministic JSON literals and control escapes, normalized negative zero, and rejected non-finite or unsupported identity values.
- Added byte-level canonical serialization and SHA-256 identity helpers.
- Added typed value classifications, blocker records, matrix row kinds/statuses, blocked freeze payload, external freeze-hash envelope, and validation primitives.
- Preserved `phase_18_authorized=true`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` in the typed blocked payload boundary.
- Added normative conformance and schema tests only; tests do not touch real data.

## TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Canonical JSON identity | `tests/phase_18/test_canonical_json.py` | Unit | N/A (new files) | Written first; initial focused collection failed before production module existed | 22 focused tests passed | Added exponent, unsupported timestamp/key, surrogate, and envelope-edge vectors; 24 passed | Export cleanup and Ruff-clean; 24 passed |
| Typed schema primitives | `tests/phase_18/test_schemas.py` | Unit | N/A (new files) | Written first; initial collection failed before schema module existed | 22 focused tests passed | Added external-hash and kind-specific matrix cases; 24 passed | Validation helpers/export cleanup; 24 passed |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/` — exit 0, **24 passed, 1 PytestCacheWarning** |
| Focused Ruff command | `python -m ruff check src/pada3dacb/publication/__init__.py src/pada3dacb/publication/canonical_json.py src/pada3dacb/publication/schemas.py tests/phase_18/test_canonical_json.py tests/phase_18/test_schemas.py` — exit 0, all checks passed |
| Runtime harness | N/A — this unit has no runtime/data boundary; it is pure CPU-only serialization and validation |
| Rollback boundary | Remove only the new `src/pada3dacb/publication/` primitives, `tests/phase_18/` focused tests, and the two implementation-progress records; no unrelated files or scientific methods are involved |

## Files changed

- `src/pada3dacb/publication/__init__.py` — public exports.
- `src/pada3dacb/publication/canonical_json.py` — canonical bytes/text and identity hash helpers.
- `src/pada3dacb/publication/schemas.py` — strict typed freeze primitives and validators.
- `tests/phase_18/test_canonical_json.py` — canonicalization conformance vectors.
- `tests/phase_18/test_schemas.py` — typed schema and blocked-state tests.
- `specs/phase_18_experiment_freeze/implementation_progress.md` — cumulative work-unit evidence.
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md` — cumulative apply evidence.

## Deviations

None from the Work Unit 1 boundary. Scientific values remain unresolved placeholders; no defaults, loaders, training, evaluation, metrics, authorization CLI, feasibility execution, resource measurement, or Phase 19 implementation was added.

The OpenSpec planning `tasks.md` was not modified because this delegated work unit has no dedicated implementation checkbox and the exact ownership boundary explicitly forbids modifying paths outside the listed work-unit files. The planning checkboxes therefore remain unchanged.

## Remaining planning tasks

The persisted planning task artifact remains unchecked and was intentionally preserved byte-for-byte:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

## Workload / chain context

- Delivery: stacked-to-main, one work unit per PR, target <=400 changed lines.
- Current PR boundary: Work Unit 1 only — canonical identity and typed schema primitives.
- Follow-up slices: matrix/provenance/feasibility/gate.
- Out of scope: real data, loaders, training/evaluation, publication metrics, real-run authorization CLI, feasibility execution, resource measurement, and Phase 19.

```text
Phase 18 planning package (scientifically blocked)
  P18-01..P18-08 -> independent review -> maintainer resolution
                              |
                              v
              📍 WU1: canonical JSON + typed schema primitives
                              |
                              v
              WU2: matrix/provenance -> WU3: synthetic feasibility
                              |
                              v
              WU4: fail-closed gate/CLI (future; no real execution)
```

No real execution occurred and no approval is claimed.

## Work Unit 3 — synthetic feasibility and machine-readable resource budget

### Status consumed and produced

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
warnings:
  - Synthetic evidence is engineering-only and cannot resolve real resource fields.
  - Authorization remains phase_18_authorized=true, freeze_approved=false, real_execution_authorized=false, publication_authorized=false, phase_19_forbidden=true.
  - No real paths, loaders, training, evaluation, metrics, authorization CLI, or Phase 19 behavior was used.
```

### Completed behavior

- Added typed `EvidenceType` values exactly `measured_synthetic`, `extrapolated_from_synthetic`, `not_recorded`, and `blocked`.
- Added explicit production-shape metadata for MRI input, feature map, ROI masks, tokens, subject embedding, concepts, `c_target`, `g_bar`, diagnosis logits, class order, and ROI order.
- Added deterministic CPU-only synthetic tensor descriptors and injectable pure forward/backward callbacks without importing training modules or accessing paths.
- Enforced faithful channels, ROI count, token/depth contracts, class order, requested batch size, and explicit engineering-only reduced-probe labeling (`non_publication_engineering_probe`).
- Added typed synthetic feasibility observations with parameter count, production input shape, requested batch, operation results, optional diagnostics, device, dtype, status, evidence type, and fixed non-authorization flags.
- Added typed resource-budget fields and explicit cell-count/storage/wall-time formulas. Synthetic memory/timing remains engineering-only and every real resource field stays `unresolved_blocking`.
- Added budget closure rejection so planning arithmetic or synthetic observations cannot authorize real throughput or close a real resource budget.
- Added a machine-readable planning payload to `specs/phase_18_experiment_freeze/resource_budget.md` preserving unresolved blockers and authorization boundaries.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Synthetic feasibility contract | `tests/phase_18/test_feasibility.py` | Unit | 48 passed | Import collection failed before `feasibility.py` existed | 9 focused tests passed | Faithful mapping/labels, wrong ROI/class shapes, failed callback, CPU boundary, reduced probe, and optional records | Canonical `c_target`/`g_bar` names and Ruff-clean; 11 passed |
| Resource budget records and closure | `tests/phase_18/test_feasibility.py` | Unit | 48 passed | Included in initial missing-module RED | 9 focused tests passed | Synthetic timing/memory, unresolved fields, formulas, and closure rejection | Shared typed field serializer; 11 passed |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/test_feasibility.py` — exit 0, **11 passed, 1 PytestCacheWarning** |
| Required suite | `python -m pytest -q tests/phase_18/` — exit 0, **59 passed, 1 PytestCacheWarning** |
| Focused Ruff command | `python -m ruff check src/pada3dacb/publication/feasibility.py tests/phase_18/test_feasibility.py` — exit 0, all checks passed |
| Runtime harness | **N/A** — this unit intentionally has no real runtime/data boundary; callbacks receive synthetic descriptors only |
| Rollback boundary | Revert only `src/pada3dacb/publication/feasibility.py`, `tests/phase_18/test_feasibility.py`, the Work Unit 3 progress sections, and the machine-readable resource payload |

### Files changed

- `src/pada3dacb/publication/feasibility.py`
- `tests/phase_18/test_feasibility.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `specs/phase_18_experiment_freeze/resource_budget.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### Deviations

None from the assigned Work Unit 3 boundary. No scientific method implementation, real-data loader, training/evaluation runner, publication metric, real authorization CLI, native receipt, unrelated dirty path, or Phase 19 behavior was changed.

### Chain context

- Delivery: stacked-to-main.
- Current boundary: **📍 Work Unit 3 — synthetic feasibility and machine-readable resource budget**.
- Start: Work Units 1–2 approved (canonical/schema primitives, matrix, and provenance).
- End: synthetic feasibility/resource schema and tests.
- Follow-up: authorization gate/CLI only; real resource closure and execution remain blocked.

```text
Phase 18 blocked planning
  WU1 canonical JSON + typed schema primitives
        |
  WU2 deterministic matrix + exact-byte provenance
        |
        📍 WU3 synthetic feasibility + resource budget
        |
  WU4 fail-closed authorization gate/CLI (follow-up)
```

No real execution occurred; synthetic observations cannot authorize real throughput or resolve lambda/method parameters, real timing, memory/storage, privacy, or resource approval. Phase 19 remains forbidden.

### Remaining planning tasks

The persisted OpenSpec planning task artifact remains unchanged because it has no dedicated Work Unit 3 implementation row and the exact delegated ownership list excludes `openspec/changes/phase-18-experiment-freeze/tasks.md`. No planning task completion is claimed. The exact unchecked rows remain:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`.

## Corrective reliability slice — Work Unit 1 blockers

**Scope:** Only REL-FALLBACK-001 and REL-FALLBACK-002 were addressed after explicit implementation review. The existing authorization boundary and unresolved scientific blockers remain unchanged.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Freeze envelope identity | `tests/phase_18/test_schemas.py` | Unit | 6 passed | Wrong well-formed digest test written first and failed | 12 focused schema tests passed after identity comparison | Valid digest, wrong 64-hex digest, and malformed digest cases pass | Minimal comparison only; Ruff-clean |
| Strict authorization/completion booleans | `tests/phase_18/test_schemas.py` | Unit | 6 passed | Integer/truthy/falsey flag tests written first and failed | 13 focused schema tests passed after exact-bool checks | Integer, string, and `None` substitutes are rejected across payload/matrix flags | Shared `_require_bool`; Ruff-clean |

### Corrective verification evidence

- Focused RED: `python -m pytest -q tests/phase_18/test_schemas.py` — exit 1, 7 expected failures before production changes.
- Focused GREEN/triangulation: `python -m pytest -q tests/phase_18/test_schemas.py` — exit 0, **13 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **31 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/schemas.py tests/phase_18/test_schemas.py` — exit 0, all checks passed.
- Runtime harness: N/A — schema identity/flag validation is pure CPU-only logic with no data or publication boundary.
- Rollback boundary: revert only the REL-FALLBACK-001/002 changes in `src/pada3dacb/publication/schemas.py`, `tests/phase_18/test_schemas.py`, and these two progress records.

### Corrective implementation

- `FreezePayloadEnvelope` now compares a supplied well-formed `freeze_hash` with `identity_sha256(payload)`.
- Freeze authorization flags and matrix invocation/completion flags now require actual `bool` values; integer and other truthy/falsey substitutes fail closed.
- `tasks.md` was not modified: no dedicated Work Unit 1 checkbox exists, and the exact delegated ownership boundary excludes it. All planning rows remain unchecked and unresolved.

### Status consumed/produced

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
warnings:
  - Workspace was heavily dirty; only the four explicitly owned paths were edited.
  - Scientific blockers and authorization boundaries remain unresolved/blocked.
  - No real data, publication, Phase 19, .git/gentle-ai, or native review command was used.
```

## Remaining planning tasks

- [ ] P18-01 through P18-10 remain unchecked in the persisted planning task artifact; no completion is claimed.
- Parent lifecycle remains responsible for review/verification routing; this executor did not create or approve receipts.

## Work Unit 2 — deterministic matrix and provenance validation

### Status consumed

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: apply
```

Authorization fields remain unchanged exactly: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true`.

### Completed behavior

- Added an explicit-seed deterministic matrix generator for the protected seven methods, canonical parser directions, complete folds `0..4`, and one linked `last` checkpoint projection per training row.
- Generated 70 training rows and 70 projection rows for planning seed `[42]`, with separate counts, stable matrix/row identities, canonical ordering, exact parent IDs, and planning-only states.
- Rejected aliases, unsupported methods, incomplete/duplicate dimensions, duplicate training rows, orphan projections, projection-as-training rows, invalid identity relationships, and completion states.
- Added exact-byte SHA-256 provenance validation with explicit JSON/YAML/CSV/TSV adapters, declared-hash verification before parsing, schema/cohort/role/subject checks, one-scan declarations, missing-file `BLOCKED_DATA`, drift `PROVENANCE_MISMATCH`, and content-level assignment disjointness.
- Aggregate assignment hashes are never used as a substitute for parsed subject-identity intersection; no artifact is regenerated.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Deterministic experiment matrix | `tests/phase_18/test_matrix.py` | Unit | N/A (new files) | Import collection failed before production module existed | Focused matrix tests passed; included in 46-test Phase 18 suite | Cardinality, ordering, explicit seeds, aliases, duplicate cells, orphan parents, and projection semantics | Identity/order validation cleanup; Ruff-clean |
| Exact-byte provenance validation | `tests/phase_18/test_provenance.py` | Unit | N/A (new files) | Import collection failed before production module existed | Focused provenance tests passed; included in 46-test Phase 18 suite | Hash stability, missing/drift, schema/role/cohort, uniqueness, one-scan, coverage, overlap, non-overlap, and explicit JSON/YAML/CSV/TSV adapters | Adapter and result contracts cleaned; Ruff-clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/` — exit 0, **46 passed, 1 PytestCacheWarning** |
| Focused Ruff command | `python -m ruff check src/pada3dacb/publication/experiment_matrix.py src/pada3dacb/publication/provenance.py tests/phase_18/test_matrix.py tests/phase_18/test_provenance.py` — exit 0, all checks passed |
| Runtime harness | N/A — this unit is CPU-only planning/validation and intentionally has no runtime/data boundary |
| Rollback boundary | Revert only `src/pada3dacb/publication/experiment_matrix.py`, `src/pada3dacb/publication/provenance.py`, `tests/phase_18/test_matrix.py`, `tests/phase_18/test_provenance.py`, and the two progress records; unrelated dirty paths remain untouched |

### Files changed

- `src/pada3dacb/publication/experiment_matrix.py`
- `src/pada3dacb/publication/provenance.py`
- `tests/phase_18/test_matrix.py`
- `tests/phase_18/test_provenance.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### Deviations

None from the Work Unit 2 boundary. No training, optimizer, MRI loader, real-data runner, publication metric, authorization CLI, synthetic device probe, resource measurement, or Phase 19 behavior was added. The planning task artifact was intentionally not modified: it has no dedicated Work Unit 2 checkbox, and the delegated exact ownership list excludes `openspec/changes/phase-18-experiment-freeze/tasks.md`.

### Chain context and dependency diagram

- Delivery: stacked-to-main.
- Current PR boundary: **📍 Work Unit 2 — deterministic matrix plus exact-byte provenance validation**.
- Start: Work Unit 1 canonicalization/schema primitives.
- End: tested planning matrix and provenance validators.
- Follow-up: synthetic feasibility/resource budget, then fail-closed authorization CLI; no real execution.

```text
Phase 18 planning package (scientifically blocked)
  P18-01..P18-08 -> independent review -> maintainer resolution
                              |
                              v
              WU1: canonical JSON + typed schema primitives
                              |
              📍 WU2: deterministic matrix + provenance validation
                              |
                              v
              WU3: synthetic feasibility/resource budget
                              |
                              v
              WU4: fail-closed authorization CLI (future)
```

No real data loading, training, evaluation, publication metrics, authorization, resource measurement, or Phase 19 execution occurred; no scientific blocker was resolved and no approval is claimed.

### Remaining planning tasks

The persisted `tasks.md` remains unchanged and all planning rows remain unchecked; no task checkbox update is claimed. Exact unchecked rows:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`.

## Corrective review-risk slice — Work Unit 2 provenance blockers

**Scope:** Only RISK-001 and RISK-002 were corrected within the existing Work Unit 2 boundary. Authorization fields, unresolved scientific blockers, and planning-only behavior remain unchanged.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| CSV/TSV per-record schema version | `tests/phase_18/test_provenance.py` | Unit | 46 passed | Mixed-schema CSV and TSV regression failed before fix | Focused provenance tests: 11 passed | Existing valid CSV/TSV adapters plus mixed-schema cases for both adapters | Minimal per-record equality check; Ruff-clean |
| Target cohort agreement before disjointness | `tests/phase_18/test_provenance.py` | Unit | 46 passed | Mixed-cohort disjointness regression failed before fix | Focused provenance tests: 11 passed | Same-cohort overlap/non-overlap plus mixed-cohort rejection | Minimal cohort guard before intersection; Ruff-clean |

### Verification evidence

- Baseline safety net: `python -m pytest -q tests/phase_18/` — exit 0, **46 passed, 1 warning**.
- RED: `python -m pytest -q tests/phase_18/test_provenance.py` — exit 1, **2 expected failures** before production changes.
- GREEN/triangulation: `python -m pytest -q tests/phase_18/test_provenance.py` — exit 0, **11 passed, 1 warning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **48 passed, 1 warning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/provenance.py tests/phase_18/test_provenance.py` — exit 0, all checks passed.
- Runtime harness: **N/A** — pure CPU-only manifest validation; no runtime, real-data, or publication boundary exists by design.
- Rollback boundary: revert only the RISK-001/RISK-002 changes in `src/pada3dacb/publication/provenance.py`, `tests/phase_18/test_provenance.py`, and these progress records.

### Corrective implementation

- CSV and TSV records now each require `schema_version` to be present and equal to the declared version; mixed-schema manifests fail with `INVALID_SCHEMA`.
- Assignment disjointness now requires adaptation and evaluation manifest cohorts to match before subject intersection can pass; mixed-cohort manifests fail with `INVALID_SCHEMA`.
- `tasks.md` remains unchanged and all planning rows remain unchecked; no planning task completion is claimed.

### Status consumed/produced

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
warnings:
  - Scientific blockers and authorization remain unresolved/blocked.
  - Only the four explicitly owned correction paths were edited.
  - No real data, publication, Phase 19, .git/gentle-ai, or native review command was used.
```

### Remaining planning tasks

The persisted `openspec/changes/phase-18-experiment-freeze/tasks.md` remains unchanged; P18-01 through P18-10 are still unchecked. Parent lifecycle remains responsible for independent review, verification, receipts, and lifecycle routing.

## Work Unit 4 — fail-closed freeze gate and read-only CLI

### Status consumed and produced

```yaml
schemaName: gentle-ai.sdd-status
schemaVersion: 1
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
warnings:
  - Structured status was authoritative; workload required the supplied stacked-to-main decision.
  - The planning task artifact was not edited because it has no Work Unit 4 checkbox and is outside the exact owned paths.
  - phase_18_authorized=true, freeze_approved=false, real_execution_authorized=false, publication_authorized=false, phase_19_forbidden=true remain unchanged.
  - No native review lifecycle command, receipt, real data, training, evaluation, publication analysis, or Phase 19 action was used.
```

### Completed behavior

- `freeze.py` validates explicit blocked-planning payloads, propagates unresolved blockers, rejects completed rows and invented/missing values, and writes canonical JSON with an external SHA-256 freeze hash.
- `validation.py` aggregates matrix, provenance, synthetic-feasibility, and explicit blocker checks with stable fail-closed codes; it never opens a data path.
- `authorization.py` requires exact flags, complete hashes, matrix/seed/scientific/artifact identity, content-level assignment disjointness, privacy, review, human approval, and native receipt evidence. `authorized: true` alone cannot pass.
- Both YAML files are planning-only and preserve unresolved scientific/resource/approval blockers.
- `prepare_publication_run.py` only prints/validates the planning matrix and blockers or writes a planning freeze artifact; it has no training/data-loader imports and never invokes training.
- `check_real_run_authorization.py` is read-only, prints every blocker, exits nonzero at closure, and emits `REAL RUN NOT AUTHORIZED` plus `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED`.

### Persisted task checkbox updates

No planning checkbox was changed. The exact ownership boundary excludes `openspec/changes/phase-18-experiment-freeze/tasks.md`; no P18 planning task completion is claimed.

### TDD Cycle Evidence

| Task slice | Test file | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| Freeze canonical envelope and blocker propagation | `tests/phase_18/test_freeze.py` | N/A (new files) | Missing-module collection failed | 4 focused tests passed | Round-trip, tamper, completed-row, and missing-field cases | Canonical-byte verification and external hash boundary; Ruff-clean |
| Authorization and validation gate | `tests/phase_18/test_authorization.py` | 59 Phase 18 tests passed | Missing-module collection failed | 8 focused tests passed | Missing field, wrong hash, unresolved science, overlap, privacy/human/native approval, CLI closure, and overwrite cases | Stable blocker formatting and strict flags/hashes; Ruff-clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/test_freeze.py tests/phase_18/test_authorization.py` — exit 0, 12 passed, 1 PytestCacheWarning |
| Required test command | `python -m pytest -q tests/phase_18/` — exit 0, **71 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check src/pada3dacb/publication/freeze.py src/pada3dacb/publication/authorization.py src/pada3dacb/publication/validation.py tests/phase_18/test_freeze.py tests/phase_18/test_authorization.py scripts/prepare_publication_run.py scripts/check_real_run_authorization.py` — exit 0 |
| Runtime harness | `python scripts/check_real_run_authorization.py --config configs/publication/real_run_authorization.yaml` — exit 1 as required; printed all blockers and the fail-closed verification line. No data path opened. |
| Rollback boundary | Remove only the Work Unit 4 modules, tests, scripts, publication configs, and this appended progress section; WU1-WU3 and unrelated dirty paths remain untouched. |

### Deviations

None from the assigned Work Unit 4 boundary. The checker intentionally remains nonzero because Phase 18 is still closed. No publication metric, target outcome, artifact regeneration, data loading, training import, or Phase 19 behavior was added.

### Workload / PR boundary

- Delivery: stacked-to-main.
- Current boundary: **📍 Work Unit 4 — fail-closed publication freeze validation plus read-only CLI preparation/checker**.
- Start: approved WU1 canonical/schema, WU2 matrix/provenance, and WU3 synthetic feasibility/resource contracts.
- End: planning freeze envelope, aggregate gate, unauthorized configs, preparation CLI, and read-only closure checker.
- Follow-up: integration tests, docs/report, and independent final audit. Real execution/publication remain forbidden by design.
- Review budget: focused stacked slice; no real execution and no native lifecycle command.

```text
WU1 canonical JSON + typed schema
  -> WU2 deterministic matrix + provenance
    -> WU3 synthetic feasibility + resource budget
      -> 📍 WU4 fail-closed freeze/authorization + read-only CLI
        -> integration validation -> docs/report -> independent final audit
```

### Remaining planning tasks

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

No real execution occurred; `REAL RUN NOT AUTHORIZED` remains the intended closure state and Phase 19 remains forbidden.

## Work Unit 5 — Phase 18 integration and closure regression tests

### Status consumed and produced

```yaml
schemaName: gentle-ai.sdd-status
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\\Users\\LOQ\\Desktop\\PADA-3DACB
  allowedEditRoots:
    - C:\\Users\\LOQ\\Desktop\\PADA-3DACB
warnings:
  - Phase 18 remains planning-only and scientifically blocked.
  - No planning checkbox was changed; the exact owned paths exclude tasks.md and contain no dedicated integration checkbox.
  - Existing unrelated dirty workspace paths were preserved.
```

### Completed behavior

- Added deterministic cross-module coverage for canonical bytes/hash and freeze round-trip identity.
- Covered value classes and unresolved propagation for `lambda_proto`, CORAL/MMD/CDAN parameters, and publication ablation blockers.
- Covered complete 140-row matrix cardinality, parser-bound directions, training/projection roles, parent IDs, and no `COMPLETED` state.
- Covered exact-byte manifest identity, schema/role/cohort checks, and content-level subject overlap.
- Covered synthetic-only feasibility and the unresolved real-resource budget boundary.
- Covered publication-package/CLI import boundaries and fail-closed authorization aggregation.
- Added CLI coverage for matrix/blocker output, validate-only, feasibility-only, planning-freeze writes, overwrite rejection, non-CPU closure, checker output, and Phase 19 closure fields.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| WU5 cross-module contracts | `tests/phase_18/test_integration.py` | Integration | N/A (new file) | Collection initially failed on an invalid non-ASCII bytes literal; corrected before production-independent test execution | 8 tests passed | Matrix, manifest overlap, synthetic boundary, unresolved science, and import-boundary cases | Ruff-clean; assertions tightened to exact contracts |
| WU5 CLI closure contracts | `tests/phase_18/test_cli.py` | Integration | N/A (new file) | One assertion exposed an over-broad expectation about blocker text; corrected to the specified feasibility-only boundary | 7 tests passed | Matrix/blocker, validate/feasibility, write/overwrite, non-CPU, checker, and Phase 19 cases | Ruff-clean; subprocess helper centralized |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused integration tests | `python -m pytest -q tests/phase_18/test_integration.py tests/phase_18/test_cli.py` — exit 0, **15 passed, 1 PytestCacheWarning** |
| Focused Phase 18 suite | `python -m pytest -q tests/phase_18/` — exit 0, **86 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check tests/phase_18/test_integration.py tests/phase_18/test_cli.py` — exit 0, all checks passed |
| Runtime harness | `test_cli.py` invokes only planning/checker CLIs with synthetic temporary output; no real-data, trainer, optimizer, MRI-loader, publication, Phase 19, native receipt, or review command was invoked |
| Rollback boundary | Remove only `tests/phase_18/test_integration.py`, `tests/phase_18/test_cli.py`, and this Work Unit 5 progress section; WU1-WU4 production paths and unrelated dirty files remain untouched |

### Deviations and remaining work

None from the assigned integration-test boundary. `real_execution_authorized=false`, `publication_authorized=false`, `freeze_approved=false`, and `phase_19_forbidden=true` remain closed. No production scientific method, preprocessing, split/artifact generator, native receipt, `.git/gentle-ai`, real data, publication output, Phase 19 file, or native review command was modified or invoked.

The persisted planning `tasks.md` remains byte-for-byte unchanged with P18-01 through P18-10 unchecked; no planning task completion is claimed.

### Workload / PR boundary

- Delivery: stacked-to-main.
- Current boundary: **📍 Work Unit 5 — integration and closure regression tests only**.
- Start: WU1-WU4 implementation and focused unit contracts.
- End: deterministic synthetic integration coverage and fail-closed CLI regression coverage.
- Follow-up: parent lifecycle verification/review routing; this executor did not create or approve receipts.
- Review budget: focused test-only slice; no production implementation or real execution.

```text
WU1 canonical/schema -> WU2 matrix/provenance -> WU3 feasibility/budget
  -> WU4 freeze/authorization CLI -> 📍 WU5 integration/closure tests
```


## Corrective Work Unit — Gemini-fallback Phase 18 findings

### Status consumed

```yaml
schemaName: gentle-ai.sdd-status
schemaVersion: 1
changeName: phase-18-experiment-freeze
artifactStore: openspec
actionContext:
  mode: repo-local
  workspaceRoot: C:\Users\LOQ\Desktop\PADA-3DACB
  allowedEditRoots:
    - C:\Users\LOQ\Desktop\PADA-3DACB
applyState: ready
nextRecommended: parent-lifecycle
warnings:
  - This is one bounded correction transaction for P18-AUTH-001, P18-AUTH-002, P18-ID-001, P18-MATRIX-001, P18-FEAS-001, and P18-ISO-001.
  - Planning tasks remain unchecked; tasks.md was outside the exact correction ownership list and was not changed.
```

### Findings and fixes

- **P18-AUTH-001:** authorization now validates the complete 140-row matrix, row identities, methods, lowercase directions, cohort mapping, folds, seed policy, unique training cells, projection parents, planning statuses, checkpoint policies, and hashes the complete canonical row set rather than trusting `matrix_id`.
- **P18-AUTH-002:** authorization now requires a complete method-parameter ledger, freeze payload identity, content-bearing hash evidence, and explicit resource-budget evidence/closure fields; arbitrary 64-hex placeholders remain blocked.
- **P18-ID-001:** `schemas.FreezePayload` and `freeze.py` share `phase18.freeze.v1`, `freeze_approved`, extensions, typed round-trip, and one `freeze_payload_hash` path.
- **P18-MATRIX-001:** default publication matrices require `[42]`; non-default seeds require an explicit resolved policy. Public method identity and direction/cohort identity are validated and row-bound.
- **P18-FEAS-001:** feasibility requires a matrix identity plus explicit forward/backward callbacks, blocks no-op calls as `RESOURCE_BLOCKED`, and enforces `g_bar_shape == (B, 102)`.
- **P18-ISO-001:** target adaptation accepts exactly `x`, `subject_id`, `subject_hash`, and `cohort`; target evaluation requires the monitoring-only label, `selection_usage=false`, and read-only metadata. Aggregate validation and authorization invoke the firewall.

### TDD Cycle Evidence

| Slice | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Complete matrix identity and default seed boundary | `tests/phase_18/test_matrix.py`, `test_integration.py` | New imports/contract tests failed during collection before production symbols existed | Focused tests passed | Forged matrix hash, custom resolved seed policy, row mutation, row identity/cohort checks | Ruff auto-fix then suite remained green |
| Freeze schema interoperability and evidence binding | `tests/phase_18/test_schemas.py`, `test_freeze.py`, `test_integration.py` | New `freeze_payload_hash`/approval-field tests failed during collection | Focused tests passed | Typed round-trip with extension fields, external hash tamper, missing evidence | Canonical mapping path retained |
| Feasibility resource blocking | `tests/phase_18/test_feasibility.py` | New callback/matrix/g_bar tests failed before implementation | Focused tests passed | Missing callbacks, wrong g_bar shape, failed callback, non-CPU request | Existing tests adapted to explicit contracts |
| Target-isolation firewall | `tests/phase_18/test_integration.py` | New validation imports failed during collection | Focused tests passed | Extra/missing adaptation fields and selection metadata violation | Provenance owns canonical firewall functions |

### Verification evidence

- `python -m pytest -q tests/phase_18/` — exit 0, **97 passed, 1 PytestCacheWarning**.
- Focused Ruff over all changed Python files — exit 0, all checks passed.
- Runtime harness: **N/A**. This correction only exercises pure schema, matrix, provenance, validation, authorization, and synthetic descriptors; no real runtime/data boundary was opened.
- Rollback boundary: revert only the listed owned publication modules/tests and these progress appendices; unrelated dirty workspace and native review artifacts remain untouched.

### Authorization and execution boundary

`phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain preserved. No ADNI/OASIS training or evaluation, publication analysis, real artifact generation, Phase 19 work, existing scientific-method/preprocessing/split changes, native review lifecycle command, receipt, or `.git/gentle-ai` path was modified or invoked.

## Corrective Work Unit — P18-AUTH-001/P18-AUTH-002 authorization boundary

### Scope

Only the authorization boundary and its tests were corrected after the prior broad correction timed out. Matrix implementation, feasibility, isolation, identity, scientific resolution, real data, publication, Phase 19, `.git/gentle-ai`, and native review commands were not touched.

### Completed behavior

- Required structured `freeze_payload`, `method_parameter_ledger`, canonical hash evidence, and explicit external/native authorization evidence.
- Rejected local/self-issued receipts, repeated fabricated 64-hex placeholders, and `authorized=true` without content-bound external evidence.
- Kept the blocked `phase18.freeze.v1` payload false fields intact; separate authorization evidence carries any future approval assertion and does not assert the blocked payload approved.
- Required resource budget closure to carry explicit external content-bound evidence rather than arbitrary mappings or synthetic/planning values.
- Kept complete matrix validation on the existing typed validators and complete-row hash; row cardinality now follows the explicit seed set, with default `[42]` and explicit resolved policy required for non-default seeds.
- Preserved propagation of unresolved scientific, freeze, ledger, assignment, artifact, review, privacy, resource, and authorization blockers.

### TDD Cycle Evidence

| Slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| External/native authorization evidence | `tests/phase_18/test_authorization.py` | 19 focused tests passed | 2 new evidence tests failed before production changes | 26 focused authorization/integration tests passed | Local/self-issued receipt and fabricated repeated digest cases | Ruff-clean |
| Structured freeze/ledger/resource evidence | `tests/phase_18/test_authorization.py` | 19 focused tests passed | Missing-field, unresolved mapping, and arbitrary-budget assertions failed before production changes | 26 focused authorization/integration tests passed | Malformed freeze payload, unresolved ledger, and arbitrary closure mapping | Ruff-clean |
| Seed-aware complete matrix validation | `tests/phase_18/test_authorization.py` | 19 focused tests passed | Explicit two-seed matrix was rejected by hard-coded 140 cardinality | 26 focused authorization/integration tests passed | Degenerate rows and explicit resolved `[7, 42]` policy | Ruff-clean |

### Verification evidence

- Focused: `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **26 passed, 1 PytestCacheWarning**.
- Required: `python -m pytest -q tests/phase_18/` — exit 0, **104 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/authorization.py src/pada3dacb/publication/validation.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0.
- Runtime harness: **N/A** — pure CPU-only authorization/matrix validation; no runtime or real-data boundary was opened.
- Rollback boundary: revert only this correction in the two publication modules, two test files, and the two progress records.

### Status and lifecycle

Structured status consumed: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, allowed root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, `nextRecommended: apply` before completion. Produced next recommendation: `parent-lifecycle`; verify remains blocked by the ten unchecked planning rows. No planning task checkbox is claimed complete; `tasks.md` remains unchanged and parent-owned lifecycle work is deferred.

No runtime/real-data work was performed. Authorization fields remain `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` in current configuration.

## Corrective Work Unit — authorization evidence binding (RISK-001 through RISK-003)

### Scope and status

This bounded stacked-to-main correction is limited to the Phase 18 authorization-evidence-binding slice. `delivery_strategy=auto-chain`, `chain_strategy=stacked-to-main`; no size exception was used. Matrix, feasibility, isolation, identity, scientific resolution, real data, publication, Phase 19, `.git/gentle-ai`, and native review commands remain out of scope.

### Completed behavior

- **RISK-001:** method-parameter ledger, resource-budget, and freeze hash evidence now require external/native provenance, canonical content hashing, and exact equality with the corresponding manifest object.
- **RISK-002:** privacy/data-access, independent review, statistical review, and human authorization require structured external/native records with content/hash binding; standalone 64-hex strings fail closed.
- **RISK-003:** the authorization gate compares top-level publication seeds with matrix seeds and rejects `[7, 42]` against frozen `[42]`.
- `validation.py` was reviewed and left unchanged. Existing target-isolation and matrix validation behavior remains intact.
- False authorization fields and unresolved scientific blockers remain preserved: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`.

### Files changed

- `src/pada3dacb/publication/authorization.py`
- `tests/phase_18/test_authorization.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### TDD Cycle Evidence

| Slice | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Exact ledger/resource evidence | 104 Phase 18 tests passed | Forged object evidence assertions failed before production changes | Focused tests passed | Ledger and budget forgeries are rejected independently | Shared canonical evidence helper; Ruff-clean |
| Structured approval attestations | 104 Phase 18 tests passed | Hash-only attestation assertions failed before production changes | Focused tests passed | Missing records and local content-bound records both fail | Shared attestation binding; Ruff-clean |
| Frozen seed/matrix binding | 104 Phase 18 tests passed | Matrix `[7, 42]` mismatch assertion failed before production changes | Focused tests passed | Mapping and typed matrix seed representations are normalized | Minimal top-level/matrix comparison; Ruff-clean |

### Work Unit Evidence

- RED: focused authorization selection exited 1 with the three new behavior assertions failing before production changes.
- GREEN/triangulation: focused selection exited 0, **4 passed, 15 deselected, 1 PytestCacheWarning**.
- Focused integration: `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **30 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **108 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/authorization.py src/pada3dacb/publication/validation.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0.
- Runtime harness: **N/A** — pure CPU-only authorization checks with no runtime/data boundary.
- Rollback boundary: revert only the RISK-001–003 changes in `authorization.py`, `test_authorization.py`, and these two progress records.

### Remaining planning tasks

No planning task is claimed complete and `tasks.md` remains unchanged. Exact unchecked rows remain:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

Parent lifecycle owns independent verification and review/receipt routing. No review, refutation, correction validation, native lifecycle, real data, publication, or Phase 19 action was started.

## Corrective Work Unit — RISK-002 external-attestation authority binding

### Scope and status

This bounded `auto-chain` / `stacked-to-main` correction addresses **RISK-002 only**: self-asserted external/native approval provenance in the Phase 18 authorization gate. The authoritative status was `gentle-ai.sdd-status` v1 with `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, and the allowed edit root set to that workspace. The current slice is **📍 external-attestation authority binding**.

Only the explicitly owned authorization/test/progress paths were considered. No native receipt or lifecycle command was modified or invoked.

### Completed behavior

- Added a process-local opaque `VERIFIER_AUTHORITY_SENTINEL`; mappings that merely claim `source: external|native` and `external: true` cannot construct or deserialize the required authority identity.
- Required the sentinel on external/native approval attestations, the authorization-evidence mapping itself, and the native receipt; prior ledger/resource hash-binding behavior was otherwise left unchanged.
- Required the native lifecycle receipt to be a native, structured, content/hash-bound record carrying the verifier authority marker; absent, malformed, self-asserted, or unverifiable receipts fail closed.
- Added negative coverage for self-asserted external and native authorization mappings and approval attestations, plus positive coverage only for the process-local verifier sentinel path.
- Preserved `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`, unresolved scientific blockers, and default seed policy behavior.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/authorization.py` | Modified | Enforced opaque verifier authority for external/native evidence and structural native receipt binding. |
| `tests/phase_18/test_authorization.py` | Modified | Added self-asserted external/native negative tests and safe sentinel-path positive tests. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative RISK-002 correction evidence. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative RISK-002 correction evidence. |

### TDD Cycle Evidence

| Slice | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| External/native authority binding | Phase 18 baseline: 108 passed | New tests failed during collection because the sentinel production symbol did not exist | Focused authority selection: 4 passed | Both `external` and `native` self-asserted mappings, four approval records, and native receipt path covered | Focused Ruff passed; helper and authority checks kept minimal |

### Verification and work-unit evidence

- Focused authority tests: `python -m pytest -q tests/phase_18/test_authorization.py -k 'self_asserted_external_native or verifier_authority_sentinel'` — exit 0, **4 passed, 19 deselected, 1 PytestCacheWarning**.
- Focused authorization/integration tests: `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **34 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **112 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/authorization.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime harness: **N/A — intentionally not run.** This correction is pure CPU-only authorization validation; no real data, publication, Phase 19, native receipt, or lifecycle command was accessed.
- Rollback boundary: revert only the RISK-002 changes in `src/pada3dacb/publication/authorization.py`, `tests/phase_18/test_authorization.py`, and these two progress records; preserve all other Phase 18 and unrelated workspace paths.

### Deviations and remaining work

None from the assigned boundary. `tests/phase_18/test_integration.py` was not changed because the focused integration regression suite already passed and no broader behavior was needed. No implementation planning task is claimed complete; the persisted `tasks.md` remains byte-for-byte unchanged with P18-01 through P18-10 unchecked because it has no row for this correction and is outside the exact delegated edit list.

Exact remaining unchecked rows are P18-01 through P18-10 in `openspec/changes/phase-18-experiment-freeze/tasks.md`. Parent lifecycle owns independent verification, bounded review/receipt routing, and delivery gates; this executor did not start them.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current boundary: **📍 external-attestation authority binding (RISK-002 only)**.
- Start: existing Phase 18 authorization gate with self-asserted external/native provenance.
- End: opaque process-local authority binding, structurally bound native receipt checks, and regression coverage.
- Out of scope: RISK-001, RISK-003, matrix, feasibility, isolation, identity, scientific resolution, real data, publication, Phase 19, `.git/gentle-ai`, native review/lifecycle commands, and actual receipt changes.

```text
Phase 18 authorization gate
  -> 📍 RISK-002 external-attestation authority binding
  -> parent lifecycle verification/review routing
```

No real execution occurred and no approval was inferred.

## Corrective Work Unit — RISK-002 authority-bound receipt hardening

### Scope and structured status

This narrow `auto-chain` / `stacked-to-main` correction supersedes the prior exported-sentinel approach for **RISK-002 only**. It consumed authoritative `gentle-ai.sdd-status` v1: `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root set to that workspace, and `nextRecommended: apply`. `verify` remains blocked by the ten unchecked planning rows; `next_recommended` after this executor is `parent-lifecycle`.

### Completed behavior

- Removed the exported `VERIFIER_AUTHORITY_SENTINEL` and replaced it with a process-local opaque authority held in a private closure; only the underscored test issuance path can obtain the identity, and config/ordinary mappings cannot construct or deserialize it.
- Authorization now checks verifier ownership by object identity rather than a public/importable sentinel.
- Native receipts require the exact `gentle-ai.review-receipt/v1` schema, native/external provenance, non-empty lineage, `gate: post-apply`, `result: allow`, the verifier-owned token, the exact content keys, matching lineage/gate/result, and a canonical content hash equal to `native_receipt_hash`.
- Arbitrary receipt content such as `{receipt: verifier-issued}`, imported/public self-assertions, malformed receipts, and mismatched lineage/gate/result fail closed.
- Existing unresolved scientific blockers and authorization boundaries remain unchanged: `authorized=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true`.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/authorization.py` | Modified | Replaced public sentinel enforcement with private process-local authority ownership and strict native receipt validation. |
| `tests/phase_18/test_authorization.py` | Modified | Added RED/GREEN coverage for public sentinel absence, arbitrary receipt rejection, lineage/gate/result mismatch, and valid verifier-issued receipt binding. |
| `tests/phase_18/test_integration.py` | Unchanged | Focused integration regression passed; no broader integration behavior was required. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative correction evidence. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative correction evidence. |

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Process-local verifier authority | `tests/phase_18/test_authorization.py` | Unit | 34 passed | Import collection failed before private issuance path existed | 5 focused authority tests passed | Public sentinel absence, arbitrary content, mismatched fields, and valid token/receipt path | Ruff-clean; private closure retained |

### Verification and work-unit evidence

- Focused authority tests: `python -m pytest -q tests/phase_18/test_authorization.py -k 'exported_verifier_sentinel or arbitrary_receipt_mapping or native_receipt_requires or verifier_authority'` — exit 0, **5 passed, 21 deselected, 1 PytestCacheWarning**.
- Focused authorization/integration tests: `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **37 passed, 1 PytestCacheWarning**.
- Focused Phase 18 suite: `python -m pytest -q tests/phase_18/` — exit 0, **115 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/authorization.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime harness: **N/A — intentionally not run.** No real data, publication, Phase 19, native receipt/lifecycle command, or real execution was accessed.
- Rollback boundary: revert only this RISK-002 correction in `authorization.py`, `test_authorization.py`, and the two progress records; preserve all unrelated paths and prior findings.

### Remaining tasks and lifecycle

No planning task checkbox was changed or claimed; `openspec/changes/phase-18-experiment-freeze/tasks.md` remains unchanged with exact unchecked rows **P18-01 through P18-10**. Parent-owned verification, review/receipt routing, and delivery gates remain deferred to `parent-lifecycle`.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current slice: **📍 authority boundary hardening (RISK-002 only)**.
- Out of scope: RISK-001, RISK-003, scientific resolution, matrix/feasibility/isolation behavior, real data, publication, Phase 19, `.git/gentle-ai`, native review commands, and actual receipt changes.

No real execution occurred; no approval was inferred.

## Corrective Work Unit — RISK-002A/RISK-002B verifier seam and target-bound receipt

### Scope and structured status

This narrow `auto-chain` / `stacked-to-main` correction addresses **RISK-002A and RISK-002B only**: importable issuer bypass and missing native-receipt target binding. Structured status consumed and produced:

```yaml
schemaName: gentle-ai.sdd-status
schemaVersion: 1
changeName: phase-18-experiment-freeze
artifactStore: openspec
applyState: ready
apply: ready
verify: blocked
archive: blocked
nextRecommended: parent-lifecycle
actionContext:
  mode: repo-local
  workspaceRoot: C:\\Users\\LOQ\\Desktop\\PADA-3DACB
  allowedEditRoots:
    - C:\\Users\\LOQ\\Desktop\\PADA-3DACB
warnings:
  - Scientific blockers and false authorization fields remain preserved.
  - No native receipt file or lifecycle/review command was modified or invoked.
  - The ten planning rows remain unchecked; no planning task completion is claimed.
```

### Completed behavior

- Removed all production issuer functions and process-local issuance state from `authorization.py`; it now accepts only a verifier callback supplied by the external integration seam. Direct self-issuance and missing callbacks fail closed.
- Kept the verifier token fixture private to `test_authorization.py`; no production issuance helper or sentinel is importable.
- Extended the native receipt schema and canonical content binding with exact `target_identity` and `target_hash` fields at both receipt and content levels.
- Required manifest target identity/hash to match the receipt exactly, so replaying an otherwise valid receipt for a different identity or hash fails closed.
- Preserved `phase_18_authorized=true`, `freeze_approved=false` in planning config, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`, unresolved scientific blockers, and target-isolation checks.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/authorization.py` | Modified | Removed issuer functions; added external verifier callback seam and exact target-bound native receipt validation. |
| `tests/phase_18/test_authorization.py` | Modified | Added direct issuer-access negative coverage, private verifier fixture usage, and identity/hash replay mismatch coverage. |
| `tests/phase_18/test_integration.py` | Unchanged | Existing integration regression coverage passed; no broader integration change was needed. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative correction evidence. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative correction evidence. |

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| RISK-002A verifier seam | `tests/phase_18/test_authorization.py` | Unit | 37 passed | 6 authority/receipt cases failed: importable issuer remained and new verifier API was absent | All 6 previously failing cases passed; focused suite 39 passed | Private token callback, arbitrary receipt, lineage/gate/result mismatch, and direct issuer absence | Ruff-clean; production has no issuer function |
| RISK-002B target binding | `tests/phase_18/test_authorization.py` | Unit | 37 passed | Target-bound receipt tests failed before schema/API change | Identity- and hash-replay cases passed; focused suite 40 passed | Different target identity and different target hash, with internally consistent replay hashes | Ruff-clean; exact receipt/content field sets retained |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **40 passed, 1 PytestCacheWarning** |
| Full Phase 18 focused suite | `python -m pytest -q tests/phase_18/` — exit 0, **118 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check src/pada3dacb/publication/authorization.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed |
| Runtime harness | **N/A — intentionally not run.** No real data, publication, Phase 19, native receipt file, or lifecycle/review command was accessed. |
| Rollback boundary | Revert only this RISK-002A/RISK-002B correction in `authorization.py`, `test_authorization.py`, and the two progress records; preserve all prior findings and unrelated paths. |

### Task checkbox reconciliation and remaining work

No planning task checkbox was changed or claimed. The persisted `openspec/changes/phase-18-experiment-freeze/tasks.md` was re-read and remains unchanged with these exact unchecked rows:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current slice: **📍 verifier authority and native receipt target binding (RISK-002A/RISK-002B only)**.
- Deferred lifecycle: parent-owned verification, bounded review/receipt routing, and delivery gates; this executor did not start them.
- No real execution/publication/Phase 19 occurred; no approval was inferred.

## Corrective Work Unit — P18-ID-001/P18-MATRIX-001 approved-boundary follow-up

### Scope and status

Bounded `auto-chain` / `stacked-to-main` correction for **P18-ID-001 and P18-MATRIX-001 only**, after RISK-002A/RISK-002B approval of the authorization boundary. Consumed status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, repo-local workspace `C:\Users\LOQ\Desktop\PADA-3DACB`, with the delegated path list enforced. `verify` remains blocked by the ten planning rows; parent lifecycle remains next.

### Completed behavior

- Unified `schemas.FreezePayload` and `freeze.py` on `phase18.freeze.v1`, one required-field contract, and one typed canonical `freeze_payload_hash` path, including `freeze_approved`, all required hashes/flags, and extension-preserving cross-module round trips.
- Enforced default publication seeds exactly `[42]`; `[7, 42]` is rejected unless an explicit resolved policy object declares the exact alternate set. Seed-aware row validation no longer accepts alternate seeds implicitly.
- Validated canonical method identity, lowercase direction identity, direction-to-cohort mapping, folds, row identity, planning-only status, training/projection semantics, parent links, and complete matrix content hash. Dimensions-only `matrix_id` is not treated as sufficient evidence.
- Kept counts derived from rows and preserved no `COMPLETED` rows, `freeze_approved=false`, unresolved blockers, and all real/publication/Phase 19 fail-closed fields.

### TDD Cycle Evidence

| Task slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| P18-ID-001 | `tests/phase_18/test_schemas.py`, `test_freeze.py` | 39 passed | Missing schema hash helper caused collection failure | Focused identity tests passed | Extension round trip, external hash/tamper, approval field | Ruff-clean |
| P18-MATRIX-001 | `tests/phase_18/test_matrix.py`, `test_integration.py` | 39 passed | New seed/content assertions failed before implementation | Focused matrix/integration tests passed | Default/alternate seeds, forged identity/hash, direction/cohort/projection cases | Ruff-clean |

### Evidence

- Focused: `python -m pytest -q tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py tests/phase_18/test_matrix.py tests/phase_18/test_integration.py` — exit 0, **43 passed, 1 PytestCacheWarning**.
- Required: `python -m pytest -q tests/phase_18/` — exit 0, **122 passed, 1 PytestCacheWarning**.
- Focused Ruff over all eight changed Python source/test paths — exit 0, all checks passed.
- Runtime harness: **N/A** — pure CPU-only contract validation; no runtime, real-data, publication, Phase 19, native review, or lifecycle command was run.
- Rollback boundary: revert only the four publication modules, three modified tests, and these two progress records for this slice.

### Remaining planning rows

No checkbox was changed: no dedicated implementation row exists for this correction and `tasks.md` is outside the exact delegated edit list. Exact unchecked rows remain P18-01 through P18-10 in the OpenSpec tasks artifact. Parent lifecycle owns verification, receipts, and delivery gates.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current bounded slice: **P18-ID-001/P18-MATRIX-001 only**.
- Excluded: feasibility, isolation, documentation, real data/publication, Phase 19, `.git/gentle-ai`, and native review commands.
- Next recommendation: `parent-lifecycle`.


## Corrective reliability slice — RELIABILITY-001 and RELIABILITY-002

### Scope and status

One bounded `auto-chain` / `stacked-to-main` correction addressed **RELIABILITY-001** (outer matrix identity binding) and **RELIABILITY-002** (external-only freeze hash identity) only. Structured status consumed: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root set to that workspace, and `nextRecommended: parent-lifecycle` after implementation.

### Completed behavior

- `validate_matrix_input` binds typed and mapping outer `matrix_id` values to the identity carried by fully validated complete rows. Outer-only identity mutation now fails with `hash_mismatch`.
- `FreezePayload.from_mapping` rejects internal `freeze_hash` fields, and typed extensions containing `freeze_hash` are rejected by schema validation. External envelope hashing remains the sole freeze identity path; internal hashes cannot be double-hashed.
- Matrix content hashing, complete-row validation, row/projection invariants, false authorization fields, unresolved scientific blockers, and planning-only boundaries remain unchanged.

### TDD Cycle Evidence

| Task slice | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| RELIABILITY-001 outer matrix identity | `tests/phase_18/test_matrix.py` | Outer typed/mapping regression failed before production change | Focused selection passed | Both outer-only mutations fail while validated rows/content remain intact | Shared row-derived identity helper; Ruff-clean |
| RELIABILITY-002 external freeze identity | `tests/phase_18/test_schemas.py`, `test_freeze.py` | Internal typed/mapping hash regressions failed before production change | Focused selection passed | External envelope stays valid; internal hashes reject | Single schema boundary retained; Ruff-clean |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_matrix.py tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py` — exit 1, **2 expected regression failures** before production changes.
- GREEN/triangulation: same focused selection — exit 0, **34 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **125 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/validation.py src/pada3dacb/publication/schemas.py src/pada3dacb/publication/freeze.py tests/phase_18/test_matrix.py tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime statement: **No runtime, real data, publication, Phase 19, native review/lifecycle command, `.git`, or `gentle-ai` path was accessed or modified.**

### Files changed

- `src/pada3dacb/publication/validation.py`
- `src/pada3dacb/publication/schemas.py`
- `tests/phase_18/test_matrix.py`
- `tests/phase_18/test_schemas.py`
- `tests/phase_18/test_freeze.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

`src/pada3dacb/publication/freeze.py` and `tests/phase_18/test_integration.py` were read and verified within the allowed boundary and unchanged in this correction.

### Task checkbox reconciliation and remaining work

No planning task was completed or checked. There is no dedicated checkbox for this correction, and `tasks.md` is outside the exact delegated edit list. The ten legacy implementation rows remain unchecked in the persisted OpenSpec tasks artifact; parent-owned verification, receipts, and delivery gates remain deferred.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current bounded slice: **RELIABILITY-001 and RELIABILITY-002 only**.
- Excluded: real data/publication, Phase 19, `.git/gentle-ai`, native review commands, and unrelated files.
- Next recommendation: `parent-lifecycle`.

## Corrective reliability slice — P18-FEAS-001 callback evidence

### Scope and status

One bounded `auto-chain` / `stacked-to-main` correction addressed **P18-FEAS-001 only**. Consumed structured status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root set to that workspace, and `nextRecommended: apply` before implementation. Produced recommendation: `parent-lifecycle`.

### Completed behavior

- No-op feasibility remains `RESOURCE_BLOCKED`; missing forward/backward callbacks and unresolved matrix identity cannot produce `PASS` or `production_fit_established=true`.
- Callback evidence now accepts only exact boolean results. Truthy objects, mappings, and other arbitrary callback returns fail closed with an explicit invalid-result reason; backward execution is not attempted after invalid forward evidence.
- Production-fit construction is fail-closed on status, exact callback evidence, a non-unresolved SHA-256 matrix identity, and the reduced engineering-probe label. Existing faithful `concepts`, `c_target`, and exact `g_bar == (B, 102)` shape checks remain enforced.
- Engineering-only reduced probes, synthetic evidence labels, unresolved resource fields, and all authorization boundaries remain unchanged.

### TDD Cycle Evidence

| Task slice | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| P18-FEAS-001 callback evidence | `tests/phase_18/test_feasibility.py` | Two regressions failed before the production change because arbitrary truthy returns were treated as success | Focused selection passed | Invalid forward result blocks backward invocation; invalid backward result cannot establish fit; exact booleans remain supported | Shared exact-result helper and explicit fit preconditions; Ruff-clean |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_feasibility.py -k 'arbitrary_callback_values or non_boolean_backward_result'` — exit 1, **2 expected failures** before production changes.
- GREEN: same focused selection — exit 0, **2 passed, 13 deselected, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **127 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/feasibility.py tests/phase_18/test_feasibility.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime statement: **No real data, runtime/publication execution, Phase 19, native review/lifecycle command, `.git`, or `gentle-ai` path was accessed or modified.** Synthetic descriptors and reduced engineering probes only; no real resource closure occurred.

### Files changed and task reconciliation

- Changed: `src/pada3dacb/publication/feasibility.py`, `tests/phase_18/test_feasibility.py`, and this progress record. `tests/phase_18/test_integration.py` was read within the allowed boundary and unchanged.
- No planning checkbox was completed or changed: the exact correction has no dedicated task row, and `openspec/changes/phase-18-experiment-freeze/tasks.md` is outside the delegated edit list. The ten legacy implementation rows remain unchecked and were re-read before return.
- Parent-owned deferred lifecycle: verification, bounded review/receipts, and delivery gates.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current bounded slice: **P18-FEAS-001 callback evidence only**.
- Excluded: target isolation, documentation/finalization, real data/publication, Phase 19, `.git/gentle-ai`, and native review commands.
- Next recommendation: `parent-lifecycle`.

## Corrective Work Unit — P18-ISO-001 target firewall enforcement

### Scope and status

This bounded `auto-chain` / `stacked-to-main` correction addresses **P18-ISO-001 only**: strict target-adaptation isolation and target-evaluation monitoring metadata enforcement. The authoritative status consumed was `gentle-ai.sdd-status` v1 with `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\Users\LOQ\Desktop\PADA-3DACB`, allowed edit root set to that workspace, and `nextRecommended: apply`. Parent lifecycle remains responsible for verification and delivery routing.

### Completed behavior

- Target adaptation now requires exactly `x`, `subject_id`, `subject_hash`, and `cohort`; identity fields are non-empty strings and inspectable nested supervision, artifact, role, cohort, and subject-identity fields are rejected rather than dropped.
- Target manifests are checked from concrete records for target role, cohort agreement, subject IDs, subject hashes, uniqueness, and forbidden nested supervision/artifact fields. A self-declared `status: VERIFIED` mapping without records cannot pass aggregate validation.
- Target evaluation requires the exact `MONITORING ONLY — NOT A TRAINING LOSS` label, actual boolean `selection_usage=False`, actual boolean `read_only=True`, and no nested selection/training-loss bypass metadata.
- Aggregate validation and authorization continue to invoke the target firewall for direct target inputs; aggregate provenance validation now inspects supplied target manifest contents instead of trusting status/role metadata alone.
- Content-level adaptation/evaluation subject intersection and all existing authorization false/unresolved blockers remain unchanged.

### Files changed

- `src/pada3dacb/publication/provenance.py` — strengthened target batch, target manifest, identity, nested-field, and monitoring-contract validation.
- `src/pada3dacb/publication/validation.py` — routed aggregate provenance and direct target inputs through strict manifest/metadata checks.
- `tests/phase_18/test_provenance.py` — added nested firewall, identity, and monitoring-bypass negative/positive tests.
- `tests/phase_18/test_authorization.py` — added authorization invocation and self-declared manifest negative tests.
- `tests/phase_18/test_integration.py` — added aggregate target-manifest content enforcement and positive concrete-manifest coverage.
- `specs/phase_18_experiment_freeze/implementation_progress.md` — appended this cumulative progress record.
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md` — appended this cumulative progress record.

`src/pada3dacb/publication/authorization.py` was inspected and remained unchanged because its existing `_check_target_isolation` call already routes supplied target inputs through `aggregate_validators`.

### TDD Cycle Evidence

| Slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Four-key target-adaptation firewall | `tests/phase_18/test_provenance.py`, `test_authorization.py` | Unit/integration | Prior persisted Phase 18 safety net: 127 passed | 2 expected firewall/identity failures before production changes | Nested diagnosis/probability/concept/artifact and role/cohort bypasses; malformed identity values; authorization routing | Shared recursive nested-field and manifest-record validation; Ruff-clean |
| Monitoring-only target evaluation | `tests/phase_18/test_provenance.py`, `test_integration.py` | Unit/integration | Prior persisted Phase 18 safety net: 127 passed | Nested selection metadata bypass failed before production changes | Wrong label, true/non-bool selection usage, read-only metadata, and nested usage fields | Exact boolean checks and recursive metadata inspection; Ruff-clean |
| Concrete target-manifest aggregation | `tests/phase_18/test_integration.py` | Integration | Prior persisted Phase 18 safety net: 127 passed | Self-declared `VERIFIED` target mapping was accepted before production changes | Concrete `ManifestValidation` records pass; status-only mapping fails | Shared provenance target-manifest helper; content-level disjointness retained |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| RED focused selection | `python -m pytest -q tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py -k 'target_adaptation_firewall or target_evaluation_contract or authorization_invokes_target_firewalls or self_declared_target_manifest or aggregate_validation_rejects_self_declared or aggregate_validation_checks_target_manifest'` — exit 1, **5 expected failures** before production changes |
| GREEN focused selection | Same selection — exit 0, **8 passed, 51 deselected** |
| Triangulation focused files | `python -m pytest -q tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **59 passed** |
| Required Phase 18 tests | `python -m pytest -q tests/phase_18/` — exit 0, **134 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check src/pada3dacb/publication/provenance.py src/pada3dacb/publication/validation.py src/pada3dacb/publication/authorization.py tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed |
| Runtime harness | **N/A — intentionally not run.** Pure CPU-only synthetic contract validation; no real data, loaders, publication, Phase 19, native review, or lifecycle command was invoked. |
| Rollback boundary | Revert only the P18-ISO-001 changes in `provenance.py`, `validation.py`, the three focused test files, and the two progress records. |

### Deviations and remaining work

No deviation from the narrow correction boundary. `authorization.py` did not require a source edit because its existing aggregate invocation is now hardened by `validation.py`. No planning task checkbox was changed: `tasks.md` contains only legacy planning rows, no dedicated implementation row for this correction, and the exact delegated edit list excludes `tasks.md`.

Exact remaining unchecked rows, re-read before return, are P18-01 through P18-10 in `openspec/changes/phase-18-experiment-freeze/tasks.md`. No planning task completion is claimed. Scientific blockers, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain preserved.

### Workload / PR boundary

- Delivery: `auto-chain`, `stacked-to-main`; no size exception.
- Current boundary: **P18-ISO-001 target-adaptation firewall and target-evaluation monitoring contract only**.
- Parent-owned deferred lifecycle: independent verification, bounded review/receipts, and delivery gates.
- Next recommendation: `parent-lifecycle`.

No real execution or approval was inferred.

### Exact remaining unchecked task lines

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

## Corrective Work Unit — RISK-001 aggregate provenance binding

### Scope and status

Bounded `auto-chain` / `stacked-to-main` correction for the new RISK-001 aggregate validation bypass only. Current slice: **📍 provenance aggregate binding**. Consumed authoritative status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `apply: ready`, `verify: blocked`, repo-local workspace `C:\Users\LOQ\Desktop\PADA-3DACB`, allowed edit root limited to that workspace, `nextRecommended: apply` before implementation. Produced recommendation: `parent-lifecycle`. No size exception was used.

### Completed behavior

- Successful `ManifestValidation` records are opaque verifier-issued values bound to exact raw bytes, SHA-256, byte size, adapter/schema parsing, immutable records, unique identities, role/cohort, and recomputed subject hashes. Caller-constructed or mutated records fail closed.
- Aggregate validation rejects self-declared `VERIFIED` mappings and caller-authored `ManifestValidation` values, requiring verifier-issued source, adaptation, and evaluation records.
- Target disjointness is recomputed from concrete verified records every time. Caller-supplied disjointness/status claims are rejected; verifier-issued disjointness must match the recomputed fingerprint and overlap result.
- Authorization now requires bound `provenance`, invokes aggregate validation, and compares assignment contents to concrete verified records. Forged/overlapping records fail closed.
- Preserved target isolation, unresolved science, and authorization false-state invariants: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`.

### Files changed

- `src/pada3dacb/publication/provenance.py`
- `src/pada3dacb/publication/validation.py`
- `src/pada3dacb/publication/authorization.py`
- `tests/phase_18/test_provenance.py`
- `tests/phase_18/test_authorization.py`
- `tests/phase_18/test_integration.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### TDD Cycle Evidence

| Slice | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| Opaque manifests/aggregate recomputation | 4 focused negative tests failed before production changes | 4 focused tests passed | Forged records, self-declared manifests/disjointness, concrete overlap | Immutable snapshots, private authority marker, recomputed fingerprint; Ruff-clean |
| Authorization binding | Forged-manifest authorization assertion failed before production changes | Focused authorization/integration selection passed | Missing/forged provenance and overlapping records fail closed | Narrow aggregate blocker routing and assignment binding |

### Evidence and boundaries

- RED: focused Phase 18 selection for caller-constructed/self-declared/authorization cases — exit 1, **4 expected failures**.
- GREEN: same selection — exit 0, **4 passed, 59 deselected, 1 PytestCacheWarning**.
- Required: `python -m pytest -q tests/phase_18/` — exit 0, **138 passed, 1 PytestCacheWarning**.
- Ruff: focused Ruff over the six source/test paths — exit 0, all checks passed.
- No real data/loaders/training/evaluation/publication/Phase 19/native review/lifecycle/.git/gentle-ai command or path was used or modified; tests used synthetic temporary manifests only.
- No planning checkbox was changed: `tasks.md` has no dedicated correction row and is outside the exact ownership list. Parent lifecycle owns verification, bounded review/receipts, and delivery gates. Rollback is limited to the six implementation/test paths and these two progress records.

Exact remaining unchecked task lines remain P18-01 through P18-10 in the persisted OpenSpec task artifact. No approval or receipt was created. Next recommendation: `parent-lifecycle`.

## Corrective Work Unit — RISK-001 nested supervision rejection

### Scope and structured status

This bounded `auto-chain` / `stacked-to-main` correction addresses **RISK-001 only**: target-adaptation firewall rejection of nested supervision and artifact aliases. Structured status consumed and produced: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `apply: ready`, `verify: blocked`, `archive: blocked`, repo-local workspace `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root limited to that workspace, and `nextRecommended: parent-lifecycle` after implementation. No size exception was used.

### Completed behavior

- Expanded the strict target-adaptation denylist with `y`, `class_label`, `concept_target(s)`, `jacobian_target(s)`, and `anatomical_target(s)` alongside existing supervision/artifact aliases.
- Applied recursive forbidden-key inspection to every adaptation value, including nested mapping/list values inside `x`; exact top-level adaptation keys remain `x`, `subject_id`, `subject_hash`, and `cohort`.
- Added regression coverage for `y`, `class_label`, and the complete alias set at nested mapping/list depth.
- Preserved verifier-issued record binding, content-level target overlap checks, target evaluation monitoring-only metadata, and all authorization false/unresolved blockers.

### Files changed

- `src/pada3dacb/publication/provenance.py`
- `tests/phase_18/test_provenance.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

`tests/phase_18/test_authorization.py` and `tests/phase_18/test_integration.py` were re-read and executed but unchanged in this narrow correction.

### TDD Cycle Evidence

| Task slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| Nested target-adaptation aliases | `tests/phase_18/test_provenance.py` | Phase 18 baseline: 138 passed | New alias regression failed before production change | Focused alias test: 1 passed | 15 aliases, including `y`/`class_label`, nested in mapping/list values; existing firewall cases retained | Ruff-clean; recursive loop generalized from `x` to every batch value |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_provenance.py -k target_adaptation_firewall_rejects_supervision_aliases_recursively` — exit 1, expected missing rejection.
- GREEN: same focused selection — exit 0, **1 passed, 16 deselected, 1 PytestCacheWarning**.
- Focused regression files: `python -m pytest -q tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **64 passed, 1 PytestCacheWarning**.
- Required Phase 18 suite: `python -m pytest -q tests/phase_18/` — exit 0, **139 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/provenance.py tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime harness: **N/A — intentionally not run.** No real data, loaders, training, evaluation, publication, Phase 19, native review/lifecycle command, `.git/gentle-ai`, or publication command was accessed.
- Rollback boundary: revert only the nested-alias changes in `provenance.py`, `test_provenance.py`, and these two progress records.

### Deviations, remaining work, and ownership

No deviation from the requested narrow correction. No planning checkbox was changed: `tasks.md` contains only legacy planning rows, no dedicated correction row, and is outside the exact delegated edit list. Parent-owned verification, bounded review/refutation/correction validation, receipts, and delivery gates remain deferred to `parent-lifecycle`.

Exact remaining unchecked task lines, re-read before return:

- [ ] **P18-01** Create the normative requirements and value-class ledger. Owner: `claude-code`. Depends on: Phase 17 closure and Phase 18 decisions. Owns: `specs/phase_18_experiment_freeze/requirements.md`, `scientific_resolution.md`.
- [ ] **P18-02** Create the technical design and deterministic matrix/schema contracts. Owner: `opencode`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/design.md`, `experiment_matrix.md`, `freeze_schema.md`.
- [ ] **P18-03** Create acceptance criteria and provenance/hash freeze. Owner: `claude-code`. Depends on: P18-01 and P18-02. Owns: `specs/phase_18_experiment_freeze/acceptance.md`, `provenance_freeze.md`.
- [ ] **P18-04** Define synthetic faithful-shape feasibility and unresolved resource budget. Owner: `gemini-cli`. Depends on: P18-02. Owns: `specs/phase_18_experiment_freeze/feasibility_protocol.md`, `resource_budget.md`.
- [ ] **P18-05** Define the fail-closed real-run gate, CLI contract, and future execution sequence. Owner: `opencode`. Depends on: P18-03 and P18-04. Owns: `specs/phase_18_experiment_freeze/real_run_gate.md`, `execution_plan.md`.
- [ ] **P18-06** Audit repository/manuscript alignment without rewriting manuscript text. Owner: `kimi`. Depends on: P18-01. Owns: `specs/phase_18_experiment_freeze/manuscript_alignment.md`.
- [ ] **P18-07** Maintain the machine-readable ownership plan. Owner: `opencode`. Depends on: P18-01 through P18-06. Owns: `specs/phase_18_experiment_freeze/agent_plan.yaml`.
- [ ] **P18-08** Mirror the planning package into OpenSpec and keep state blocked. Owner: `opencode`. Depends on: P18-07. Owns: this change directory only.
- [ ] **P18-09** Perform independent specification review. Owner: `kimi`. Depends on: P18-08. Owns: reviewer output only; no runtime paths.
- [ ] **P18-10** Resolve scientific blockers and authorize any later transition. Owner: `maintainer`. Depends on: P18-09. Owns: explicit decision/approval records only; does not infer values from outcomes.

No real execution occurred; no approval or receipt was created. Next recommendation: `parent-lifecycle`.

## Consolidated final implementation closure

### Closure status

**`PHASE18_COMPLETE_BUT_BLOCKED_FOR_REAL_EXECUTION`**. WU1-WU5 plus bounded corrections are implementation-complete and focused-verified. This does not claim scientific freeze approval, real-run authorization, publication authorization, a native receipt, final repository-wide closure, or Phase 19 readiness.

The authorization invariants remain exactly:

```yaml
phase_18_authorized: true
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

### Consolidated evidence

- `python -m pytest -q tests/phase_18/` — exit 0, **139 passed**, 1 `PytestCacheWarning`, 6.91s.
- Editable install — exit 0; import/version — exit 0; version `0.1.0`.
- `python -m ruff check .` — exit 0.
- Scoped Phase 18 `git diff --check` — exit 0.
- Global `git diff --check` — exit 2 only for pre-existing `AGENTS.md:928` trailing whitespace; it was not changed.
- `python -m pytest -q` — attempted with a 1200-second timeout and timed out around 27%; no full-suite pass is claimed.
- `prepare_publication_run.py` print-matrix, print-blockers, feasibility-only, and validate-only modes fail closed and print blockers; no real data/training was run.
- `check_real_run_authorization.py` exits 1 and prints `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED`; authorization remains false.
- Static publication package/CLIs have no trainer, optimizer, or MRI-loader imports.

### Agents, fallback review, and lifecycle boundary

Codex implemented the work units. `review-risk` and `review-resilience` supplied implementation review. The Gemini-mapped fallback used `gentle-ai-explore`/`gentle-ai-verify`; Kimi was unavailable. `gentle-ai-verify` performed the fresh independent final audit, which retained partial acceptance because the full suite timed out and the closure artifacts were stale before this consolidation. Native lifecycle review/receipt commands were not run, and no receipt or approval was fabricated.

### Scientific and data closure boundary

No target-guided values were selected. `lambda_proto` remains **BLOCKED** between `0.2` and `1.0`; CORAL/MMD/CDAN parameters and publication ablations remain unresolved. Seed planning is `[42]`; checkpoint policy is `best_source_f1` plus separate `last` projection. The plan is 70 training rows plus 70 projection rows. Canonical JSON, matrix/provenance identity, target firewall, synthetic feasibility, and implementation tests are complete, but real manifests, real provenance hashes, immutable artifacts, real resource observations, privacy/data authorization, and human/native approval are absent.

### State and explicit non-execution

OpenSpec is now `status: blocked_for_real_execution`, `current_phase: implementation_complete`, `execution_mode: implementation_only`, with `real_run_gate: blocked` and `publication_gate: blocked`. Full regression remains unverified due timeout. No real ADNI/OASIS data, runtime execution, publication analysis, native receipt, Phase 19 work, or real feasibility/resource measurement occurred. A compact project-scoped Engram completion record was saved; OpenSpec remains the file-based source of truth.
