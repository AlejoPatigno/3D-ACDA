# Apply Progress — Phase 18 Experiment Freeze

## Status

- `artifactStore`: `openspec`
- `applyState`: `ready`
- `verify`: `blocked` until the planning task artifact is complete
- `nextRecommended`: `parent-lifecycle`
- `actionContext.mode`: `repo-local`
- Authorization fields unchanged: `phase_18_authorized=true`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`.

## Completed work unit

**📍 Work Unit 1 — canonical JSON identity plus strict typed freeze/schema primitives.**

Created only the owned implementation/test/progress paths:

- `src/pada3dacb/publication/__init__.py`
- `src/pada3dacb/publication/canonical_json.py`
- `src/pada3dacb/publication/schemas.py`
- `tests/phase_18/test_canonical_json.py`
- `tests/phase_18/test_schemas.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

Implemented `phase18.canonical-json.v1`: UTF-8 bytes, NFC strings/keys, lexicographic object keys, preserved arrays, deterministic literals/control escaping/numbers, negative-zero normalization, finite-number enforcement, unsupported-value rejection, and SHA-256 helpers. Implemented typed value classes, blockers, matrix row/status primitives, blocked freeze payload, external freeze hash envelope, and authorization-independent validation.

## TDD Cycle Evidence

| Slice | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| Canonical JSON | Focused tests written before production; collection failed while module was absent | 22 tests passed | Exponents, controls, Unicode, arrays, non-finite values, unsupported timestamps/keys, and byte stability covered; 24 passed | Exports and formatting cleaned; 24 passed |
| Typed schemas | Focused tests written before production; collection failed while module was absent | 22 tests passed | Explicit evidence, blocked authorization, matrix kind rules, and external hash boundary covered; 24 passed | Validation/export cleanup; 24 passed |

## Verification evidence

- `python -m pytest -q tests/phase_18/` — exit 0, **24 passed, 1 warning** (Pytest cache permission warning only).
- Focused Ruff over changed Python files — exit 0, all checks passed.
- Runtime harness: `N/A`; this unit is pure CPU-only serialization/schema validation and does not access real data or execute a runtime path.
- Rollback boundary: remove only the new publication package, focused Phase 18 tests, and these two progress records.

## Remaining planning tasks

The planning `tasks.md` checkboxes remain unchanged because no dedicated Work Unit 1 implementation checkbox exists and the exact delegated ownership boundary forbids modifying `tasks.md`. No task completion is claimed. The exact unchecked rows are preserved in `specs/phase_18_experiment_freeze/implementation_progress.md`.

## Chain context

Stacked-to-main; current PR contains Work Unit 1 only and targets <=400 changed lines. Follow-up: matrix/provenance/feasibility/gate slices. No real execution occurred; no freeze approval is claimed; Phase 19 was not started.

## Corrective reliability slice — Work Unit 1 blockers

**Scope:** REL-FALLBACK-001 and REL-FALLBACK-002 only, after explicit implementation review. Existing authorization boundaries and unresolved blockers were preserved.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Freeze envelope identity | `tests/phase_18/test_schemas.py` | Unit | 6 passed | Wrong well-formed digest test failed before fix | 12 focused schema tests passed | Valid, wrong 64-hex, and malformed digest cases | Minimal identity comparison; Ruff-clean |
| Strict authorization/completion booleans | `tests/phase_18/test_schemas.py` | Unit | 6 passed | Integer/truthy/falsey flag tests failed before fix | 13 focused schema tests passed | Integer, string, and `None` substitutes rejected | Shared exact-bool helper; Ruff-clean |

### Corrective verification evidence

- RED: `python -m pytest -q tests/phase_18/test_schemas.py` — exit 1, 7 expected failures before production changes.
- GREEN/triangulation: `python -m pytest -q tests/phase_18/test_schemas.py` — exit 0, **13 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **31 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/schemas.py tests/phase_18/test_schemas.py` — exit 0, all checks passed.
- Runtime harness: N/A — pure schema identity/flag validation has no runtime/data boundary.
- Rollback boundary: revert only the corrective changes in `src/pada3dacb/publication/schemas.py`, `tests/phase_18/test_schemas.py`, and these two progress records.

### Corrective implementation

- `FreezePayloadEnvelope` now requires a supplied `freeze_hash` to equal `identity_sha256(payload)`.
- Freeze authorization flags and matrix invocation/completion flags require actual `bool` values, rejecting integer and other truthy/falsey substitutes.
- `tasks.md` remains byte-for-byte unchanged: no dedicated Work Unit 1 checkbox exists and the exact delegated ownership boundary excludes it. Planning rows remain unchecked and unresolved.

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

- [ ] P18-01 through P18-10 remain unchecked in `openspec/changes/phase-18-experiment-freeze/tasks.md`; no completion is claimed.
- Parent lifecycle remains responsible for review/verification routing; this executor did not create or approve receipts.

## Work Unit 2 — deterministic matrix and provenance validation

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
  - Scientific values and authorization remain unresolved/blocked.
  - Only the six explicitly owned Work Unit 2 paths were created or modified.
```

Authorization fields preserved exactly: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`.

### Completed work

- `src/pada3dacb/publication/experiment_matrix.py`: explicit-seed deterministic seven-method × two-direction × five-fold matrix, 70 training rows plus 70 linked `last` projections for `[42]`, stable identities, counts, ordering, and fail-closed validation.
- `src/pada3dacb/publication/provenance.py`: exact-byte SHA-256 records, explicit JSON/YAML/CSV/TSV adapters, hash-before-parse, missing/drift statuses, schema/cohort/role/subject checks, one-scan declarations, and content-level assignment disjointness.
- `tests/phase_18/test_matrix.py` and `tests/phase_18/test_provenance.py`: CPU-only synthetic temporary-file coverage for cardinality, row semantics, aliases, duplicates, exact bytes, missing/drift, schema, role/cohort, coverage, overlap, and explicit JSON/YAML/CSV/TSV adapters.

### Persisted task checkbox updates

No planning checkbox was changed. `openspec/changes/phase-18-experiment-freeze/tasks.md` has no dedicated Work Unit 2 implementation row and is outside the exact delegated ownership list; all existing P18-01 through P18-10 rows remain unchecked. This is intentional and no task completion is claimed.

### TDD Cycle Evidence

| Task slice | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| Deterministic matrix | New tests failed collection before `experiment_matrix.py` existed | Focused tests passed; Phase 18 suite passed | Cardinality/order/seeds, aliases, dimensions, duplicates, parent IDs, projection roles | Identity validation and ordering cleanup; Ruff-clean |
| Exact-byte provenance | New tests failed collection before `provenance.py` existed | Focused tests passed; Phase 18 suite passed | Hash, missing/drift, schema, role/cohort, uniqueness, one-scan, coverage, overlap/non-overlap, JSON/YAML/CSV/TSV | Adapter/result cleanup; Ruff-clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/` — exit 0, **46 passed, 1 PytestCacheWarning** |
| Focused Ruff command | `python -m ruff check src/pada3dacb/publication/experiment_matrix.py src/pada3dacb/publication/provenance.py tests/phase_18/test_matrix.py tests/phase_18/test_provenance.py` — exit 0, all checks passed |
| Runtime harness | N/A — pure CPU-only planning/validation; no runtime/data boundary exists by design |
| Rollback boundary | Revert the two WU2 modules, their two tests, and these two progress records only; unrelated dirty paths remain untouched |

### Chain context

- Strategy: stacked-to-main.
- Current boundary: **📍 Work Unit 2 — deterministic matrix plus exact-byte provenance validation**.
- Start: Work Unit 1 canonicalization/schema primitives.
- End: deterministic matrix and provenance validation tested.
- Follow-up: synthetic feasibility/resource budget, then authorization CLI; no real execution.

```text
Phase 18 blocked planning
  WU1 canonical JSON + typed schema primitives
        |
        📍 WU2 deterministic matrix + provenance validation
        |
        WU3 synthetic feasibility/resource budget
        |
        WU4 fail-closed authorization CLI (future)
```

No real data loading, training, evaluation, publication metrics, authorization CLI, synthetic device probe, resource measurement, scientific blocker resolution, or Phase 19 execution occurred.

### Remaining tasks

- [ ] P18-01 through P18-10 remain unchecked in the persisted planning task artifact; no completion is claimed.
- Parent lifecycle remains responsible for independent review, verification, receipts, and lifecycle routing. This executor did not create or approve receipts.

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
  - Authorization preserved: phase_18_authorized=true, freeze_approved=false, real_execution_authorized=false, publication_authorized=false, phase_19_forbidden=true.
  - No real paths, loaders, training, evaluation, metrics, authorization CLI, native receipts, or Phase 19 behavior were used.
```

### Completed tasks and persisted checkbox updates

- Work Unit 3 implementation completed. No planning checkbox was changed: the persisted `tasks.md` has no dedicated Work Unit 3 implementation row, and the exact delegated ownership boundary excludes that file. P18-01 through P18-10 remain unchecked; no planning task completion is claimed.

### Completed behavior

- `src/pada3dacb/publication/feasibility.py` now provides typed synthetic observations, faithful production-shape validation, deterministic CPU-only tensor descriptors, pure callback seams, exact evidence types, reduced-probe labeling, and fixed non-authorization flags.
- Resource-budget records retain unresolved real device, memory, storage, wall-time, workers, retry, and concurrency fields. Explicit planning formulas expose `7 × 2 × 5 × 1 = 70` primary cells and 70 sensitivity projections.
- `specs/phase_18_experiment_freeze/resource_budget.md` contains the machine-readable planning payload and preserves all unresolved blockers.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Synthetic feasibility | `tests/phase_18/test_feasibility.py` | Unit | ✅ 48 passed | ✅ Missing-module collection failure | ✅ 9 focused tests | ✅ Faithful labels/shapes, reduced probe, callback failure, CPU boundary, optional records | ✅ Canonical `c_target`/`g_bar` names; 11 passed |
| Resource budget | `tests/phase_18/test_feasibility.py` | Unit | ✅ 48 passed | ✅ Missing-module collection failure | ✅ 9 focused tests | ✅ Synthetic timing/memory, unresolved fields, arithmetic, closure rejection | ✅ Typed field serializer; 11 passed |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `python -m pytest -q tests/phase_18/test_feasibility.py` — exit 0, **11 passed, 1 PytestCacheWarning** |
| Required test command | `python -m pytest -q tests/phase_18/` — exit 0, **59 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check src/pada3dacb/publication/feasibility.py tests/phase_18/test_feasibility.py` — exit 0, all checks passed |
| Runtime harness | **N/A** — no real runtime/data boundary exists; callbacks receive synthetic descriptors only |
| Rollback boundary | Revert only the WU3 feasibility module/test, WU3 progress sections, and machine-readable resource payload |

### Files changed

- `src/pada3dacb/publication/feasibility.py`
- `tests/phase_18/test_feasibility.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `specs/phase_18_experiment_freeze/resource_budget.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### Deviations and remaining work

None from the assigned boundary. Follow-up is the fail-closed authorization gate/CLI only. Real data/training/evaluation/publication metrics, real authorization, resource closure, and Phase 19 remain out of scope and blocked.

### Chain context

Stacked-to-main; **📍 Work Unit 3** starts after approved Work Units 1–2 and ends at synthetic feasibility/resource schema plus tests. Follow-up is the authorization gate/CLI slice. No real execution occurred and no approval is claimed.

```text
WU1 canonical/schema -> WU2 matrix/provenance -> 📍 WU3 synthetic feasibility/budget -> WU4 authorization gate/CLI
```

No real execution statement: synthetic observations cannot authorize throughput or resolve lambda/method parameters, real timing, memory/storage, privacy, or resource approval; `phase_19_forbidden=true` remains preserved.

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


## Corrective Work Unit — Gemini-fallback verification findings

### Scope and status

One bounded stacked-to-main correction transaction addressed only P18-AUTH-001, P18-AUTH-002, P18-ID-001, P18-MATRIX-001, P18-FEAS-001, and P18-ISO-001. Structured status consumed: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, allowed root `C:\Users\LOQ\Desktop\PADA-3DACB`, `nextRecommended: parent-lifecycle`. Planning task checkboxes remain unchanged and unchecked because `tasks.md` is outside the exact delegated correction paths and has no implementation checkbox for this work unit.

### Fixes

- Authorization validates and hashes complete canonical matrix rows, including methods, lowercase directions, cohort mapping, folds, resolved seed policy, unique training cells/IDs, projection parents, statuses, checkpoint policies, and row count; `matrix_id` is not trusted as proof.
- Authorization requires a complete scientific method-parameter ledger, content-bearing hash evidence, freeze payload identity, and resource-budget evidence/closure fields; arbitrary 64-hex placeholders do not satisfy evidence.
- `FreezePayload` and `freeze.py` now share `phase18.freeze.v1`, `freeze_approved`, extension-preserving typed round-trip, and one canonical payload hash helper.
- Default publication matrix generation enforces `[42]`; non-default seeds require an explicit resolved policy. Public method and cohort identities are validated and row-bound.
- Synthetic feasibility blocks no-op calls, requires explicit matrix identity and forward/backward callbacks, and validates `g_bar_shape == (B, 102)`.
- Strict target-adaptation/evaluation firewall accepts exactly the approved fields and requires monitoring-only/read-only metadata; aggregate validation and authorization call it.

### Files changed

- `src/pada3dacb/publication/schemas.py`
- `src/pada3dacb/publication/freeze.py`
- `src/pada3dacb/publication/authorization.py`
- `src/pada3dacb/publication/validation.py`
- `src/pada3dacb/publication/experiment_matrix.py`
- `src/pada3dacb/publication/feasibility.py`
- `src/pada3dacb/publication/provenance.py`
- `tests/phase_18/test_schemas.py`
- `tests/phase_18/test_freeze.py`
- `tests/phase_18/test_authorization.py`
- `tests/phase_18/test_matrix.py`
- `tests/phase_18/test_feasibility.py`
- `tests/phase_18/test_provenance.py`
- `tests/phase_18/test_integration.py`
- `specs/phase_18_experiment_freeze/implementation_progress.md`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`

### TDD Cycle Evidence

| Slice | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| Matrix/auth identity and seed policy | New regression imports/behavior failed before implementation | Focused tests passed | Forged complete matrix hash, custom resolved seed policy, row mutation, identity/cohort checks | Ruff-clean |
| Freeze schema/hash interoperability and evidence | New helper/approval tests failed before implementation | Focused tests passed | Extension-preserving round-trip, tamper, missing content evidence | Ruff-clean |
| Feasibility firewall | New no-op/callback/shape tests failed before implementation | Focused tests passed | Missing callbacks, missing matrix identity, wrong g_bar shape, callback failure | Ruff-clean |
| Target isolation | New strict-field/metadata tests failed during collection before implementation | Focused tests passed | Extra/missing fields and selection usage violation | Canonical firewall placed in provenance and invoked through aggregate validation |

### Test evidence

- `python -m pytest -q tests/phase_18/` — exit 0, **97 passed, 1 PytestCacheWarning**.
- Focused Ruff for every changed Python source/test path listed above — exit 0, all checks passed.
- Runtime harness: `N/A` — pure CPU-only contract tests and synthetic descriptors; no runtime/data boundary exists for this correction.
- Rollback boundary: revert only the owned source/test/progress changes listed above; unrelated dirty workspace, existing methods/preprocessing/splits/real artifacts, `.git/gentle-ai`, and native review artifacts remain untouched.

### Remaining work and lifecycle

- Exact unchecked planning rows remain P18-01 through P18-10; no planning task completion is claimed.
- Parent lifecycle owns independent re-verification and any review/receipt routing. This executor did not start bounded review, refutation, correction validation, or native lifecycle commands.
- No real ADNI/OASIS training/evaluation, publication analysis, Phase 19, authorization, or freeze approval occurred.

## Corrective Work Unit — P18-AUTH-001/P18-AUTH-002 authorization boundary

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
  workspaceRoot: C:\\Users\\LOQ\\Desktop\\PADA-3DACB
  allowedEditRoots:
    - C:\\Users\\LOQ\\Desktop\\PADA-3DACB
warnings:
  - This slice is limited to P18-AUTH-001 and P18-AUTH-002 after the prior broad correction timeout.
  - Scientific blockers and false authorization fields remain preserved.
  - No tasks.md checkbox was changed; the planning rows do not represent this correction slice and tasks.md is outside the exact ownership list.
```

### Completed behavior

- Authorization now requires structured `freeze_payload`, `method_parameter_ledger`, hash evidence, and explicit external/native authorization evidence; `authorized: true` and local/self-issued evidence cannot bypass the gate.
- Freeze payload validation remains compatible with the blocked `phase18.freeze.v1` schema. Approval is represented only by the separate authorization evidence mapping; blocked payload fields are not asserted approved.
- Repeated/fabricated 64-hex placeholders are rejected, and native receipt evidence must bind canonical content to `native_receipt_hash`.
- Resource budgets require explicit external content-bound closure evidence; arbitrary mappings and synthetic/planning placeholders cannot close the budget.
- Complete matrix validation still uses the existing typed matrix validator and complete-row content hash. Row cardinality derives from the explicit seed set instead of hard-coding 140; default publication seed policy remains `[42]`, while non-default seeds require an explicit resolved policy.
- Unresolved freeze and method-ledger blockers propagate as authorization blockers. Existing duplicate, invalid method/direction/fold, projection-as-training, parent-link, and matrix-hash checks remain fail-closed.

### TDD Cycle Evidence

| Slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| External/native authorization evidence | `tests/phase_18/test_authorization.py` | 19 focused tests passed | 2 new evidence tests failed before production changes | 26 focused authorization/integration tests passed | Local/self-issued receipt and fabricated repeated digest cases | Ruff-clean |
| Structured freeze/ledger and unresolved propagation | `tests/phase_18/test_authorization.py` | 19 focused tests passed | Missing-field and unresolved mapping assertions failed before production changes | 26 focused authorization/integration tests passed | Missing mappings, malformed freeze payload, and unresolved ledger values | Ruff-clean |
| Seed-aware complete matrix validation | `tests/phase_18/test_authorization.py` | 19 focused tests passed | Explicit two-seed matrix was rejected by the hard-coded cardinality | 26 focused authorization/integration tests passed | Degenerate rows and explicit resolved `[7, 42]` policy | Ruff-clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Required test command | `python -m pytest -q tests/phase_18/` — exit 0, **104 passed, 1 PytestCacheWarning** |
| Focused test command | `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **26 passed, 1 PytestCacheWarning** |
| Focused Ruff | `python -m ruff check src/pada3dacb/publication/authorization.py src/pada3dacb/publication/validation.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0 |
| Runtime harness | **N/A** — authorization and matrix checks are pure CPU-only validation; no real-data/runtime boundary exists and no runtime/real-data work was performed |
| Rollback boundary | Revert only the P18-AUTH-001/P18-AUTH-002 changes in `authorization.py`, `validation.py`, `test_authorization.py`, and these two progress records; preserve all other Phase 18 and unrelated workspace work |

### Workload / PR boundary

- Delivery: stacked-to-main; one narrow correction work unit.
- Current boundary: **📍 P18-AUTH-001/P18-AUTH-002 authorization boundary and tests**.
- Start: prior Phase 18 authorization implementation with independent-audit critical findings.
- End: external/content-bound authorization evidence, structured freeze/ledger/resource closure checks, and seed-aware complete matrix validation.
- Out of scope: matrix implementation changes, feasibility, isolation, identity, scientific resolution, real data, publication, Phase 19, `.git/gentle-ai`, and native review commands.

### Remaining work

- [ ] P18-01 through P18-10 remain unchecked in the persisted planning task artifact; no planning task completion is claimed.
- Parent lifecycle owns verification, bounded review/receipts, and lifecycle routing.

## Blocked apply attempt — Phase 18 authorization correction

- **Status:** blocked before code edits.
- **Reason:** the authoritative `tasks.md` Review Workload Forecast requires a resolved delivery path before apply (`Decision needed before apply: Yes`, `Chained PRs recommended: Yes`, `400-line budget risk: High`). The delegated prompt requires a bounded correction but does not explicitly provide `auto-chain`, a chosen chained/stacked PR mode, or `size:exception` approval.
- **Decision needed:** confirm the delivery path, preferably `stacked-to-main` for this narrow correction, or explicitly approve `size:exception` if a single PR is intended.
- **Scope held:** no source/test edits, no task checkbox changes, and no review/native lifecycle commands were performed. Requested paths remain untouched by this blocked attempt.

### Status consumed

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
  - Review Workload Forecast decision is unresolved for this apply invocation.
  - Scientific blockers and false authorization fields remain preserved.
  - No real data, publication, Phase 19, .git/gentle-ai, or native review command was used.
```

## Corrective Work Unit — authorization evidence binding (RISK-001 through RISK-003)

### Scope and status

This bounded stacked-to-main correction is limited to the Phase 18 authorization-evidence-binding slice. The delivery decision is resolved as `delivery_strategy=auto-chain`, `chain_strategy=stacked-to-main`; no size exception was used. Matrix implementation, feasibility, isolation, identity, scientific resolution, real data, publication, Phase 19, `.git/gentle-ai`, and native review commands remain out of scope.

Structured status consumed and produced:

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
  - Native status is authoritative; ten planning rows remain unchecked.
  - Scientific blockers and false authorization fields remain preserved.
  - No real data, publication, Phase 19, .git/gentle-ai, or native review command was used.
```

### Completed behavior

- **RISK-001:** hash evidence for the method-parameter ledger, resource-budget object, and freeze payload now requires external/native provenance, canonical content hashing, and exact equality with the manifest object; declared non-placeholder digests or forged mappings cannot substitute for the bound object.
- **RISK-002:** privacy/data-access, independent review, statistical review, and human authorization now require structured records whose canonical content hash matches the corresponding hash and whose provenance is external/native; standalone 64-hex strings fail closed.
- **RISK-003:** authorization now compares the top-level seed policy with the matrix seed set after validating the policy hash, rejecting a `[7, 42]` matrix when the frozen top-level policy is `[42]`.
- `validation.py` was reviewed and left unchanged; existing aggregate target-isolation and matrix validation behavior is preserved.
- `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain unchanged.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/authorization.py` | Modified | Bound ledger/budget evidence to exact canonical objects, added structured attestation validation, and enforced top-level/matrix seed equality. |
| `tests/phase_18/test_authorization.py` | Modified | Added negative tests for forged object evidence, hash-only attestations, local attestations, and seed mismatch. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative correction evidence. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative correction evidence. |

### TDD Cycle Evidence

| Slice | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Exact ledger/resource evidence | Phase 18 baseline: 104 passed | Focused assertions failed before production changes | Focused authorization tests passed | Forged ledger and budget contents are rejected independently | Seed normalization retained; Ruff-clean |
| Structured approval attestations | Phase 18 baseline: 104 passed | Hash-only attestations failed before production changes | Focused authorization tests passed | Missing records and local content-bound records both fail | Shared content-bound helper; Ruff-clean |
| Frozen seed/matrix binding | Phase 18 baseline: 104 passed | `[7, 42]` matrix mismatch assertion failed before production changes | Focused authorization tests passed | Explicit matrix object/list seed normalization covered | Minimal comparison in authorization gate; Ruff-clean |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_authorization.py -k 'hash_evidence_must_bind or approval_hashes_require or top_level_seed_policy or attestation_content_binding'` — exit 1 before the production correction, with the three new behavior assertions failing.
- GREEN/triangulation: same focused selection — exit 0, **4 passed, 15 deselected, 1 PytestCacheWarning**.
- Focused integration: `python -m pytest -q tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, **30 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **108 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/authorization.py src/pada3dacb/publication/validation.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime harness: **N/A** — pure CPU-only authorization validation; no runtime/data/publication boundary exists or was opened.
- Rollback boundary: revert only the RISK-001–003 changes in `authorization.py`, `test_authorization.py`, and these two progress records; preserve all other Phase 18 and unrelated workspace paths.

### Remaining tasks and lifecycle

No planning task is claimed complete; `tasks.md` was not edited because this correction has no corresponding planning checkbox and it is outside the exact delegated edit list. Exact unchecked rows remain:

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

Parent lifecycle owns independent verification and any review/receipt routing. This executor did not start bounded review, refutation, correction validation, or delivery gates.

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

This bounded `auto-chain` / `stacked-to-main` correction addresses **P18-ID-001 and P18-MATRIX-001 only**, after the authorization boundary was approved through the RISK-002A/RISK-002B correction. Consumed authoritative status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\Users\LOQ\Desktop\PADA-3DACB`, allowed root set to that workspace. The exact delegated edit boundary was narrower than the allowed root and was respected.

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
  - Workload forecast was high-risk; delivery was resolved as auto-chain/stacked-to-main.
  - Scientific and real-execution blockers remain preserved.
  - No real data, publication, Phase 19, .git/gentle-ai, or native review/lifecycle command was used.
```

### Completed behavior

- `schemas.FreezePayload` and `freeze.py` now share one `phase18.freeze.v1` identity contract, central required-field list, and canonical typed `freeze_payload_hash` path. `freeze_approved`, all required hashes, authorization flags, and extension fields survive typed/mapping round trips.
- Publication seed validation is exactly `[42]` by default. Alternate seeds require a resolved policy whose declared seeds match; default generation and row validation reject `[7, 42]` without that object.
- Matrix validation binds canonical method/direction/cohort/fold identities, seed policy, row identity, planning-only state, projection parent identity, and a complete-row `matrix_content_hash`; dimensions-only `matrix_id` is not sufficient.
- Matrix counts remain derived from actual training/projection rows. No hard-coded `140` was introduced in this correction, while default `[42]` still produces 70 training plus 70 projection rows.
- Existing `freeze_approved=false`, no `COMPLETED` rows, and all authorization/unresolved blockers remain fail-closed.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/schemas.py` | Modified | Centralized freeze required fields and canonical payload hashing; added typed identity helper. |
| `src/pada3dacb/publication/freeze.py` | Modified | Reused the schema version, required-field contract, and canonical hash helper. |
| `src/pada3dacb/publication/experiment_matrix.py` | Modified | Added seed-policy-aware row validation, matrix identity binding, and serialized content hash. |
| `src/pada3dacb/publication/validation.py` | Modified | Verified mapping content hashes and passed resolved seed policy through complete-matrix validation. |
| `tests/phase_18/test_schemas.py` | Modified | Added extension-preserving cross-module freeze hash/round-trip coverage. |
| `tests/phase_18/test_matrix.py` | Modified | Added alternate-seed, identity, and resolved-policy regressions. |
| `tests/phase_18/test_integration.py` | Modified | Added aggregate validation coverage for forged matrix content hashes. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative progress. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative progress. |

`tests/phase_18/test_freeze.py` was read and executed but not modified in this slice.

### TDD Cycle Evidence

| Task slice | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| P18-ID-001 freeze identity | `tests/phase_18/test_schemas.py`, `test_freeze.py` | Unit | 39 passed | Import collection failed before the schema hash helper existed | Extension-preserving typed/mapping round trip, external hash boundary, and tamper coverage | Ruff-clean; one shared helper retained |
| P18-MATRIX-001 seed and content identity | `tests/phase_18/test_matrix.py`, `test_integration.py` | Unit/integration | 39 passed | New row-policy/content-hash assertions failed before implementation | `[42]` default, rejected `[7,42]`, explicit alternate policy, forged dimensions/content identity, direction/cohort/projection checks | Ruff-clean; row-derived counts retained |

### Verification and work-unit evidence

- RED: focused collection failed with the expected missing `schemas.freeze_payload_hash` import before production changes.
- GREEN/triangulation: `python -m pytest -q tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py tests/phase_18/test_matrix.py tests/phase_18/test_integration.py` — exit 0, **43 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **122 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/schemas.py src/pada3dacb/publication/freeze.py src/pada3dacb/publication/experiment_matrix.py src/pada3dacb/publication/validation.py tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py tests/phase_18/test_matrix.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime harness: **N/A — intentionally not run.** Pure CPU-only schema/matrix/validation logic; no runtime, real-data, publication, Phase 19, native review, or lifecycle path was opened.
- Rollback boundary: revert only the four listed publication modules, the three modified tests, and the two progress appendices from this slice; preserve authorization.py, feasibility/isolation/provenance work, unrelated dirty paths, `.git/gentle-ai`, and native artifacts.

### Task checkbox reconciliation and remaining work

No planning checkbox was changed or claimed. The persisted `openspec/changes/phase-18-experiment-freeze/tasks.md` has no dedicated checkbox for this correction and is outside the exact delegated edit list. Its legacy implementation rows remain unchecked and were re-read before return:

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
- Current slice: **P18-ID-001/P18-MATRIX-001 only**.
- Boundary: schema/freeze identity interoperability plus publication matrix seed/content identity validation; feasibility, isolation, documentation, real execution, publication, Phase 19, and native review remain out of scope.
- Parent lifecycle owns verification, bounded review/receipts, and delivery gates; this executor did not launch them.
- Status after apply: implementation complete for this slice; `next_recommended: parent-lifecycle`.


## Corrective reliability slice — RELIABILITY-001 and RELIABILITY-002

### Scope and status

One bounded `auto-chain` / `stacked-to-main` correction addressed **RELIABILITY-001** (outer matrix identity binding) and **RELIABILITY-002** (external-only freeze hash identity) only. Consumed structured status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `actionContext.mode: repo-local`, workspace root `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root set to that workspace, and `nextRecommended: parent-lifecycle` after implementation. The authoritative planning state remains blocked by unresolved scientific and authorization blockers.

Authorization fields remain unchanged: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true`.

### Completed behavior

- `validate_matrix_input` now binds a typed `ExperimentMatrix.matrix_id` and mapping `matrix_id` to the shared identity carried by the fully validated complete rows. Mutating only the outer identity now returns a `hash_mismatch` blocker.
- `FreezePayload.from_mapping` rejects an internal `freeze_hash`, and typed payload extensions containing `freeze_hash` are rejected by schema validation. The existing schema/module hash helper remains one external-envelope identity path; internal hashes cannot be double-hashed.
- Existing complete-row `matrix_content_hash`, row identity, projection-parent, seed-policy, authorization, false-field, unresolved-science, and planning-only invariants remain preserved.

### Files changed

- `src/pada3dacb/publication/validation.py`
- `src/pada3dacb/publication/schemas.py`
- `tests/phase_18/test_matrix.py`
- `tests/phase_18/test_schemas.py`
- `tests/phase_18/test_freeze.py`
- `openspec/changes/phase-18-experiment-freeze/apply-progress.md`
- `specs/phase_18_experiment_freeze/implementation_progress.md`

`src/pada3dacb/publication/freeze.py` and `tests/phase_18/test_integration.py` were within the allowed boundary, read/verified, and unchanged in this correction.

### TDD Cycle Evidence

| Task slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| RELIABILITY-001 outer matrix identity | `tests/phase_18/test_matrix.py` | 122 Phase 18 tests passed | Outer typed/mapping identity regression failed before production change | Focused matrix/schema/freeze selection passed | Typed and mapping outer-only mutation, while complete rows and content hash remain validated | Shared row-derived outer-identity helper; Ruff-clean |
| RELIABILITY-002 external freeze identity | `tests/phase_18/test_schemas.py`, `test_freeze.py` | 122 Phase 18 tests passed | Internal typed/mapping freeze-hash regressions failed before production change | Focused matrix/schema/freeze selection passed | External envelope remains valid; internal typed extensions and mappings reject double/internal hashing | Single schema boundary retained; Ruff-clean |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_matrix.py tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py` — exit 1, **2 expected regression failures** before production changes.
- GREEN/triangulation: same focused selection — exit 0, **34 passed, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **125 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/validation.py src/pada3dacb/publication/schemas.py src/pada3dacb/publication/freeze.py tests/phase_18/test_matrix.py tests/phase_18/test_schemas.py tests/phase_18/test_freeze.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime statement: **No runtime, real data, publication, Phase 19, native review/lifecycle command, `.git`, or `gentle-ai` path was accessed or modified.**
- Rollback boundary: revert only this correction in `validation.py`, `schemas.py`, the three modified tests, and these two progress records; preserve all other Phase 18 and unrelated workspace paths.

### Task checkbox reconciliation and remaining work

No planning task was completed or checked. The exact delegated correction has no dedicated task row, and `openspec/changes/phase-18-experiment-freeze/tasks.md` is outside the exact edit list. Its legacy implementation rows remain unchecked and were re-read before return:

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
- Current slice: **RELIABILITY-001 and RELIABILITY-002 only**.
- Parent-owned deferred lifecycle: verification, bounded review/receipts, and delivery gates.
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

### Scope and structured status

Bounded `auto-chain` / `stacked-to-main` correction for the new **RISK-001 aggregate validation bypass** only. Current slice: **📍 provenance aggregate binding**. Consumed authoritative status: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `apply: ready`, `verify: blocked`, `actionContext.mode: repo-local`, workspace root `C:\Users\LOQ\Desktop\PADA-3DACB`, allowed edit root limited to that workspace, and `nextRecommended: apply` before implementation. Produced recommendation: `parent-lifecycle`.

The review workload decision was resolved by the delegated prompt as `delivery_strategy=auto-chain`, `chain_strategy=stacked-to-main`; no size exception was used. Planning task rows are legacy implementation rows with no dedicated correction task; no checkbox was changed.

### Completed behavior

- `ManifestValidation` success records are now verifier-issued opaque records bound to exact raw bytes, SHA-256, byte size, adapter/schema parsing, immutable parsed records, unique subject identities, role/cohort, and recomputed subject-hash consistency. Caller-constructed or mutable forged records fail closed.
- Aggregate provenance validation rejects self-declared `VERIFIED` mappings and caller-authored `ManifestValidation` objects. It requires verifier-issued records for source, target adaptation, and target evaluation.
- Target adaptation/evaluation disjointness is recomputed from the concrete verified records on every aggregate validation. Caller-supplied status/disjointness mappings are rejected; verifier-issued disjointness results must match the recomputed fingerprint and overlap status.
- Authorization now requires bound `provenance` evidence, invokes aggregate provenance validation, and compares assignment contents to the concrete verified subject records. Forged or overlapping records fail closed.
- Existing target isolation, unresolved scientific blockers, and authorization false-state invariants remain preserved: `phase_18_authorized=true`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true`.

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

| Slice | Test file | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| Opaque validated manifests and aggregate recomputation | `test_provenance.py`, `test_integration.py` | Existing Phase 18 suite passed before the slice | 4 focused negative tests failed before production changes | 4 focused tests passed | Caller-constructed records, self-declared manifests/disjointness, and concrete overlap recomputation | Immutable record snapshots, private authority marker, recomputed fingerprint; Ruff-clean |
| Authorization binding | `test_authorization.py`, `test_integration.py` | Existing authorization/integration tests remained green after RED tests | Forged manifest authorization assertion failed before production changes | Focused authorization/integration selection passed | Missing/forged provenance and overlapping concrete target records fail closed | Aggregate blocker routing and assignment-content binding kept narrow |

### Verification and work-unit evidence

- RED: `python -m pytest -q tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py -k 'caller_constructed_verified_manifest or self_declared_manifest_and_disjointness or authorization_recomputes_bound_assignment_overlap or authorization_rejects_caller_constructed_verified_manifest'` — exit 1, **4 expected failures** before production changes.
- GREEN focused selection: same command — exit 0, **4 passed, 59 deselected, 1 PytestCacheWarning**.
- Required suite: `python -m pytest -q tests/phase_18/` — exit 0, **138 passed, 1 PytestCacheWarning**.
- Focused Ruff: `python -m ruff check src/pada3dacb/publication/provenance.py src/pada3dacb/publication/validation.py src/pada3dacb/publication/authorization.py tests/phase_18/test_provenance.py tests/phase_18/test_authorization.py tests/phase_18/test_integration.py` — exit 0, all checks passed.
- Runtime/no-real-execution statement: **No real data, loaders, training, evaluation, publication, Phase 19, `.git/gentle-ai`, native review, lifecycle, or publication command was run or modified.** Tests used synthetic temporary manifests only.
- Rollback boundary: revert only the RISK-001 changes in the six implementation/test paths above and these two progress records; preserve unrelated workspace paths and prior WU invariants.

### Deviations, remaining work, and ownership

No deviation from the exact bounded correction boundary. `tasks.md` was not edited because it contains no dedicated correction row and is outside the exact ownership list. Parent-owned verification, bounded review/refutation/correction validation, receipts, and delivery gates remain deferred to `parent-lifecycle`.

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

Next recommendation: `parent-lifecycle`. No approval or receipt was created.

## Corrective Work Unit — RISK-001 nested supervision rejection

### Scope and structured status

This bounded `auto-chain` / `stacked-to-main` correction addresses **RISK-001 only**: target-adaptation firewall rejection of nested supervision and artifact aliases. Structured status consumed and produced: `gentle-ai.sdd-status` v1, `artifactStore: openspec`, `applyState: ready`, `apply: ready`, `verify: blocked`, `archive: blocked`, repo-local workspace `C:\\Users\\LOQ\\Desktop\\PADA-3DACB`, allowed edit root limited to that workspace, and `nextRecommended: parent-lifecycle` after implementation. No size exception was used.

### Completed behavior

- Expanded the strict target-adaptation denylist with `y`, `class_label`, `concept_target(s)`, `jacobian_target(s)`, and `anatomical_target(s)` alongside existing supervision/artifact aliases.
- Applied recursive forbidden-key inspection to every adaptation value, including nested mapping/list values inside `x`; exact top-level adaptation keys remain `x`, `subject_id`, `subject_hash`, and `cohort`.
- Added regression coverage for `y`, `class_label`, and the complete alias set at nested mapping/list depth.
- Preserved verifier-issued record binding, content-level target overlap checks, target evaluation monitoring-only metadata, and all authorization false/unresolved blockers.

### Files changed

| File | Action | What was done |
|---|---|---|
| `src/pada3dacb/publication/provenance.py` | Modified | Expanded recursive target-adaptation forbidden aliases and checked every batch value. |
| `tests/phase_18/test_provenance.py` | Modified | Added recursive nested alias regressions, including `y` and `class_label`. |
| `specs/phase_18_experiment_freeze/implementation_progress.md` | Modified | Appended cumulative correction evidence. |
| `openspec/changes/phase-18-experiment-freeze/apply-progress.md` | Modified | Appended cumulative correction evidence. |

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

## Final scientific-freeze synchronization

### Status

`PHASE18_SCIENTIFIC_FREEZE_COMPLETE_BUT_EXTERNAL_PROVENANCE_BLOCKED` is the authoritative final status for this metadata-only synchronization. Scientific decisions are resolved for pre-run planning; external provenance, resources, review, native lifecycle, and human authorization remain blocked.

### Synchronized records

- Both publication configurations contain the API-generated 420-row matrix: 210 training rows and 210 linked checkpoint projections. Every projection has `training_invocation=false`.
- Both configurations contain the exact seven-method parameter ledger with mapping-valued `parameters` and `evidence`, explicit value classes, and content-bound ledger identity.
- The exact resolved policy is `[42,43,44]` with source split random state `42`, target partition seed `42`, predeclared selection, and posthoc selection forbidden; top-level and matrix-embedded policies match.
- The scientific resolution hash, matrix content hash, seed policy hash, and canonical freeze hash were recomputed through repository APIs. No external hash was invented.
- Nested freeze blockers contain only external provenance, resource, review, native lifecycle, and human authorization blockers; resolved scientific and ablation choices are not blockers.

### Boundaries

`scientific_freeze_complete=true`, `real_run_ready=false`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, `phase_19_forbidden=true`, and `authorized=false` remain explicit. No real data, training, evaluation, publication analysis, native lifecycle command, receipt, or Phase 19 work occurred.

### Validation evidence

- Full regression final candidate: `python -m pytest -q -p no:cacheprovider --basetemp=C:/Users/LOQ/AppData/Local/Temp/pada3dacb-full-suite-final` — exit 0, 1325 passed, 6 warnings, 1213.18s (0:20:13); cache plugin disabled for Windows cache interference.
- Focused Phase 18 command for this synchronization: `python -m pytest -q tests/phase_18/` — current worker result recorded below after execution.
- `python -m ruff check .`, `git diff --check`, repeated canonical hash check, and the fail-closed authorization checker are recorded below after execution.

### Final synchronization validation evidence

- `python -m pytest -q tests/phase_18/ -p no:cacheprovider --basetemp=C:/Users/LOQ/AppData/Local/Temp/pada3dacb-phase18-final` — exit 0, **147 passed**, 22.76s.
- `python -m ruff check .` — exit 0, all checks passed.
- `git diff --check` — exit 0 after removing serializer-emitted trailing whitespace from the two owned YAML configurations.
- Repeated canonical hash check — exit 0 for both configurations: matrix content hash `4856bff8fd631f10c6473194064365d8bb55bb72ce5e5b68e4ca3209f3bf82ea`; scientific resolution hash `3421e7d764986496a58eb5a83506ed2e68c8b478f8ae45dbaf5676120de27fb0`; method parameter ledger hash `dff9e3917728889737fe1582aaa6f9cecc21fb2d63ec11dfbed5654dffd7f979`; seed policy hash `9a7d5c7c8130c8b434709a1240398f5d5ee5d487760268a6b4f1aa48a82dbb71`; canonical freeze hash `153e6baeb16211dd4aae9d226dbf1be1a8930831b956ee2780af90a7f3b4adb6`.
- `python scripts/check_real_run_authorization.py --config configs/publication/real_run_authorization.yaml` — exit 1 as required; printed `REAL RUN NOT AUTHORIZED` and `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED`.

No real data, training, evaluation, publication, native lifecycle, receipt, or Phase 19 action was run. The final full regression passed with the cache plugin disabled; no source/test failure remained.
