# Phase 15 Predictive Evaluation — Technical Design

## Decision summary

Implement the new, read-only `src/pada3dacb/evaluation/` package whose pure statistical core is isolated from schema-family readers and output orchestration. It consumes only configured immutable exports, normalizes all seven approved methods into one canonical subject-level contract, validates provenance and complete ensembles before statistics, and writes schema-v2 artifacts atomically. It never imports or invokes training code.

Normative bindings:

- Statistical protocol: `phase15-statistical-v2`
- Output schema: `phase15-output-v2`
- Classes: `(CN, MCI, AD) = (0, 1, 2)`
- Approved methods: `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, `faster_snn`
- Approved directions: `adni_to_oasis`, `oasis_to_adni`
- Policies: `primary_best_source_f1`; optional separate `sensitivity_last`

## Architecture and dependencies

The production package is exactly `src/pada3dacb/evaluation/`; the CLI is exactly `scripts/evaluate.py`, and the documented normal configuration argument is exactly `--config configs/evaluation/predictive.yaml`. The CLI has no implicit configuration default. No other evaluation production modules or subpackages are designed.

| Required file | Responsibility | May depend on | Must not depend on |
|---|---|---|---|
| `src/pada3dacb/evaluation/__init__.py` | Minimal public exports and protocol/schema version constants | `schemas.py` | I/O, training |
| `src/pada3dacb/evaluation/schemas.py` | Enums, frozen dataclasses, config/result/error-code schemas, typed request-failure wrapper, canonical serialization and evaluation-identity helpers without I/O | stdlib, NumPy typing | filesystem, training |
| `src/pada3dacb/evaluation/discovery.py` | Load the explicitly supplied `--config PATH` (normally `configs/evaluation/predictive.yaml`); apply CLI overrides/selectors; resolve only configured paths; group candidates; implement the explicit shared-method/baseline-combined readers and seven-method registry | stdlib, YAML, `schemas.py`, `provenance.py` | statistics, writers, training registries/imports |
| `src/pada3dacb/evaluation/provenance.py` | Streaming exact-byte SHA-256, sanitized root-relative paths, cross-file hydration/source-rule records, probability/duplicate/label/provenance validation, approved supplied subject-hash verification | stdlib, NumPy, `schemas.py` | statistics, output, training |
| `src/pada3dacb/evaluation/aggregation.py` | Source OOF completeness and target fold-then-seed validation/aggregation | NumPy, `schemas.py` | discovery I/O, writers, training |
| `src/pada3dacb/evaluation/metrics.py` | Twelve aggregate and required per-class metrics with status/reason | NumPy, scikit-learn, `schemas.py` | I/O, training |
| `src/pada3dacb/evaluation/confusion_matrices.py` | Fixed 3x3 count and nullable row-normalized matrices | NumPy, scikit-learn, `schemas.py` | I/O, training |
| `src/pada3dacb/evaluation/bootstrap.py` | True-class-stratified subject bootstrap and percentile CIs | NumPy, metric callables, `schemas.py` | I/O, training |
| `src/pada3dacb/evaluation/paired_statistics.py` | Exact McNemar and paired stratified bootstrap differences | NumPy, SciPy, metric callables, `schemas.py` | I/O, training |
| `src/pada3dacb/evaluation/multiple_testing.py` | Direct deterministic six-hypothesis Holm adjustment | `schemas.py` | statsmodels in production, I/O |
| `src/pada3dacb/evaluation/tables.py` | Exact schema-v2 CSV/table/PNG projections and atomic single-artifact writers | stdlib CSV/JSON/YAML, plotting library, `schemas.py` | discovery, training |
| `src/pada3dacb/evaluation/report.py` | Run-mode state machines; manifests/root outputs; computational extraction; whole-run staging/commit; overwrite/reuse verification; partial-failure orchestration | all required evaluation modules | training |
| `scripts/evaluate.py` | Argparse, exact selector conflicts, sanitized console reporting, and exit-code mapping only | `evaluation.discovery`, `evaluation.report`, `evaluation.schemas` | training imports, statistical implementation |
| `configs/evaluation/predictive.yaml` | Explicit file patterns, schema-family assignment, expected folds/seeds, approved companions/rules, selectors, gates, and defaults; contains no secret or raw ID | configuration data only | executable logic |
| `pyproject.toml` *(required dependency update)* | Declare every direct production dependency and test-only statsmodels placement | packaging metadata | implicit/transitive direct imports |

Optional changes to `src/pada3dacb/exceptions.py` or `src/pada3dacb/config.py` are unnecessary for this design; use them only if implementation proves an existing shared contract must be extended, never to create hidden evaluation behavior.

Dependency direction is one-way: `scripts/config -> report -> discovery/provenance/aggregation -> pure protocol modules -> tables`. The statistical core (`metrics.py`, `confusion_matrices.py`, `bootstrap.py`, `paired_statistics.py`, `multiple_testing.py`) accepts canonical in-memory values and performs no filesystem access, logging, plotting, or configuration lookup.

## Canonical contracts

### Enums

- `MethodId`: the seven approved method IDs only.
- `Direction`: `ADNI_TO_OASIS`, `OASIS_TO_ADNI`, each carrying fixed source/target cohorts.
- `CheckpointPolicy`: `PRIMARY_BEST_SOURCE_F1`, `SENSITIVITY_LAST`; logical checkpoint and policy are never pooled.
- `PredictionRole`: `SOURCE_OOF`, `TARGET_EVALUATION`.
- `AnalysisMode`: `REAL`, `SYNTHETIC_TEST_ONLY`.
- `RunMode`: `DRY_RUN`, `VALIDATE_ONLY`, `EVALUATE`, `REUSE`.
- `ValueStatus`: `AVAILABLE`, `UNAVAILABLE`, `NOT_RECORDED`.
- `CandidateStatus`: `INCLUDED`, `EXCLUDED`, `INCOMPLETE`.

### Frozen dataclasses

- `EvaluationRequest`: resolved selectors, roots, methods, directions, policies, folds, seeds, bootstrap settings, mode, overwrite/reuse, configured file patterns, approved companion rules, authorization/gate hashes.
- `InputFile`: sanitized root-relative path, exact-byte hash, size, schema family/version.
- `ProvenanceValue[T]`: non-identity provenance value, source kind, source file hash, optional deterministic derivation rule; it MUST NOT derive `subject_hash`.
- `ProvenanceRecord`: every exact field required by output schema v2, plus all contributing input hashes and equality checks.
- `CanonicalPrediction`: method, direction, seed, fold, logical checkpoint, role, stable `subject_hash`, true label, float64 probability vector, provenance reference.
- `NormalizedBatch`: adapter/schema identity, input files, provenance records, predictions, computational records, issues.
- `SubjectPrediction`: one final canonical row with ordered probabilities, fixed-order argmax, fold/seed counts, source hashes.
- `MetricValue`: `value: float | int | None`, status, stable reason; available implies finite/non-null and unavailable implies null/reason.
- `MetricSet`, `PerClassMetric`, `ConfusionResult`, `BootstrapInterval`, `PairedDifference`, and `HolmRow` mirror protocol-v2 fields; `McNemarResult` additionally carries optional informational `note_code`, with `reason=null` whenever status is available.
- `ComputationalValue`: field, nullable value, unit, status/reason, source hash.
- `EvaluationPlan`: expected candidate matrix and exact intended outputs; contains no statistics.
- `EvaluationBundle`: identity-bound canonical subject tables and all derived machine results.

Arrays are immutable-by-convention contiguous NumPy `float64`; labels are integer arrays and all public core interfaces assert shape, dtype, finiteness, and explicit `[0,1,2]` ordering.

### Error taxonomy

Typed exceptions terminate the request: `ConfigurationError`, `SelectorConflictError`, `UnsafePathError`, `ExistingOutputError`, `ReuseVerificationError`, `AuthorizationGateError`, `SchemaVersionError`, `OutputCommitError`, `InternalInvariantError`.

Data defects become visible exclusions, not crashes. Candidate validation uses this normative `IssueCode` table; protocol metric-unavailability reasons are a separate namespace and MUST NOT be emitted as candidate issue codes.

| IssueCode | Candidate defect |
|---|---|
| `unsupported_method` | Unapproved method. |
| `unsupported_direction` | Unapproved direction. |
| `unsupported_checkpoint_policy` | Unapproved checkpoint policy. |
| `unsupported_class_order` | Unapproved class order. |
| `missing_required_field` | Required field lacks an approved source. |
| `unapproved_identity_mapping` | Identity mapping is not approved. |
| `provenance_conflict` | Provenance sources conflict. |
| `input_hash_mismatch` | Input hash differs from declared hash. |
| `target_evaluation_membership_unprovable` | Target-evaluation membership cannot be proven. |
| `unstable_subject_identity` | Stable cross-file supplied identity cannot be proven. |
| `raw_identifier_persistence_attempt` | Raw identifier persistence was attempted. |
| `duplicate_prediction` | Canonical prediction key is duplicated. |
| `inconsistent_true_label` | Subject true labels conflict. |
| `non_finite_probability` | Probability is not finite. |
| `probability_out_of_range` | Probability is outside `[0,1]`. |
| `probability_sum_invalid` | Probability row sum violates tolerance. |
| `incomplete_ensemble` | Required fold or seed is absent. |
| `checkpoint_policy_mismatch` | Candidate checkpoint and selected policy differ. |
| `incompatible_subjects` | Paired subject sets or labels differ. |

Exceptions and logs carry sanitized paths and aggregate context only—never raw identifiers, labels, or probabilities.

## Adapter and provenance flows

### Shared-method family

1. Discovery expands only configured paths under `runs_root`, rejects escapes/symlinks resolving outside the root, sorts normalized relative paths, and hashes exact bytes before parsing.
2. `SharedMethodAdapter` parses configured exports read-only and verifies declared schema family/version and approved method mapping.
3. For every required provenance field, hydration uses this precedence: exact row value, approved run manifest, approved fold result, approved companion. Each value records source kind, exact source hash, and derivation rule when derived.
4. Values repeated across rows/files must be equal. Any conflict records both sanitized source references/hashes and excludes the candidate. Missing non-identity provenance fields are derivable only through configured approved rules; this allowance excludes `subject_hash`; otherwise exclude. `atlas_hash`/`roi_order_hash` require a value or proven `not_applicable`.
5. Subject identity consumes only a stable `subject_hash` supplied by an approved prediction export or approved identity companion mapping. Phase 15 does not generate, transform, salt, define, or derive subject hashes. A raw identifier may be held transiently only to cross-check an approved supplied raw-ID-to-`subject_hash` mapping whose companion hash and rule are recorded. If a stable cross-file hash cannot be proven, exclude with `unstable_subject_identity`. Raw IDs are discarded immediately after verification and are forbidden in canonical dataclasses, logs, errors, and outputs.
6. Rows are converted to `CanonicalPrediction`; validation rejects invalid probabilities, labels, duplicates, inconsistent metadata, or checkpoint mixing.

### Baseline-combined family

The same six steps apply, but `BaselineCombinedAdapter` first partitions the combined export by the explicit approved method/direction/seed/fold/checkpoint/role keys. It must not infer membership from filenames or target outcomes. Shared metadata is hydrated into each partition only after exact equality checks against row-level and companion values. Source-Only is included only when `target_evaluation_assignment_hash` proves exact target-evaluation membership; otherwise it is excluded as `target_evaluation_membership_unprovable`.

Both adapters return the identical `NormalizedBatch`; downstream code cannot branch on schema family. Every contributing file hash remains ordered and attached to provenance and final subject rows.

## Execution state machines

### Common prefix

`PARSE -> RESOLVE_SELECTORS -> DISCOVER -> HASH -> GROUP -> PROVENANCE_VALIDATE -> PLAN`

Any unsafe configuration/path is terminal. Candidate defects transition that candidate to `EXCLUDED` while processing independent candidates. Unsupported methods, directions, checkpoint policies, or class orders produce no statistics and use their exact canonical issue codes.

### Dry run

`PLAN -> REPORT_IN_MEMORY -> EXIT`

It reports grouping, expected/completed files, and incompleteness to stdout/exit status only. It does not load prediction arrays, construct ensembles, compute metrics, create the output root, or persist artifacts.

### Validate only

`PLAN -> LOAD_READ_ONLY -> NORMALIZE -> VALIDATE_ROWS -> BUILD_SOURCE_OOF/TARGET_ENSEMBLES_IN_MEMORY -> VALIDATE_PAIRING -> REPORT_IN_MEMORY -> EXIT`

It computes no bootstrap, publication metric/test, figure, evaluation identity output, or persistent file. Ensemble construction is validation work only.

### Evaluate

`PLAN -> VERIFY_REAL_GATES -> LOAD/NORMALIZE -> VALIDATE -> AGGREGATE -> FREEZE_CANONICAL_SUBJECT_TABLES -> COMPUTE_METRICS/CONFUSION -> BOOTSTRAP -> PAIRED_TESTS -> HOLM -> EXTRACT_COMPUTATIONAL -> BUILD_BUNDLE -> STAGE_OUTPUT_TREE -> VERIFY_STAGED_TREE -> ATOMIC_COMMIT -> COMPLETE`

Real mode stops before scientific statistics unless authorized exports, D-14-001, D-14-002, and independent protocol approval are hash-bound. Independent method failures remain visible in status/inclusion/header-complete files; no result is emitted for an excluded method. A request-level failure before commit leaves no selected final artifacts.

### Optional completed reuse

`RESOLVE_SELECTORS -> OPEN_EXISTING_READ_ONLY -> VERIFY_COMPLETION_MARKER/MANIFEST -> RECOMPUTE_EXPECTED_IDENTITY_INPUTS_READ_ONLY -> VERIFY_CONFIG/AUTHORIZATION/PROTOCOL/SCHEMA/LIBRARIES/ORDERED_INPUT_HASHES -> VERIFY_REQUIRED_FILE_SET/HASHES/OPTIONAL_INDEX -> REUSED`

Any mismatch transitions to `REUSE_REJECTED`; it performs no recomputation and writes nothing. `--reuse` conflicts with overwrite and all inspection modes.

## Aggregation invariants

- Source OOF: exactly one row per subject/method/direction/seed/logical checkpoint. Fold is provenance, not an averaging dimension. Duplicate or missing OOF membership invalidates the method-direction-policy.
- Target: exactly one prediction per subject for every required source fold within each configured seed. Compute a float64 arithmetic fold mean first, retaining per-seed diagnostics, then an arithmetic mean across every predeclared seed. Missing/duplicate fold or seed invalidates the whole method-direction-policy; partial ensembles are forbidden.
- True label must agree by `subject_hash` across folds, seeds, methods, and policies within a direction.
- Fixed-order `np.argmax` yields the smallest tied class index.
- Final rows are sorted by `subject_hash`; exactly one row exists per subject/method/direction/policy.
- Directions, roles, methods, and policies are never pooled. Pairing requires identical ordered hashes and labels; intersection-only inference is prohibited.

## Protocol-v2 statistical interfaces

```python
compute_metrics(table, *, labels=(0, 1, 2)) -> MetricSet
compute_confusion(table, *, labels=(0, 1, 2)) -> ConfusionResult
bootstrap_metrics(table, metric_fns, *, replicates: int, seed: int) -> tuple[BootstrapInterval, ...]
exact_mcnemar(reference, comparator) -> McNemarResult
paired_bootstrap(reference, comparator, metric_fns, *, replicates: int, seed: int) -> tuple[PairedDifference, ...]
adjust_holm(rows, *, family_size: Literal[6] = 6, comparator_order=...) -> tuple[HolmRow, ...]
```

`compute_metrics` emits exactly twelve aggregate metrics. Per class it computes seven distinct statistical quantities and emits eight named rows because `recall` and `sensitivity` are numerically identical aliases. Availability is checked before library calls. Log loss alone clips with float64 epsilon and renormalizes; Brier is the unscaled class sum. Undefined values remain null with protocol metric-unavailability reasons.

Confusion counts and normalized rows derive only from frozen final subject tables. Zero-support normalized rows are three nulls with `zero_true_support`.

Bootstrap uses `Generator(PCG64(seed))`, class-stratified fixed-order draws, one draw per replicate, no redraw, linear quantiles, and the `ceil(0.95B)` success threshold. Paired bootstrap applies one index vector to both methods and orients differences `prototype_pseudo - comparator`. Exact McNemar uses SciPy `binomtest`; for `d=0` it emits `status=available`, `raw_p_value=1.0`, `reason=null`, and `note_code=no_discordant_pairs`. Inferential results use null reason when available and may carry optional informational `note_code`. Holm creates exactly six rows per family separated by direction, policy, and statistic/metric; unavailable hypotheses remain present and do not shrink multiplicity.

## Output orchestration and failure semantics

The run output plan in `report.py` materializes exactly the selected schema-v2 tree directly below `output_root`, with no evaluation-ID directory. Root files always exist for a completed evaluation; selected policy trees are header-complete, and every included method has four confusion artifacts. Scientific rows and all figures/tables derive from serialized canonical subject tables plus identity-bound machine results.

All structured files and PNGs are first written to same-filesystem temporary siblings in a staging directory, flushed and closed, hashed, and schema-checked. Final publication uses atomic replace. To avoid a partially visible completed evaluation, the manifest is committed last and is the completion marker; reuse rejects a tree without the final manifest or with any hash mismatch. On failure, best-effort cleanup removes only evaluator-owned temporary siblings/staging paths.

Without `--overwrite`, any recognized selected result path fails before writing. Guarded overwrite may replace only the exact schema-v2 allowlist beneath the resolved output root; unknown files and all input paths are untouched. Existing recognized files are backed up within the same filesystem until the staged tree verifies; commit failure restores them or raises `OutputCommitError` with recovery-safe paths. Reuse is strictly read-only.

Partial candidate failures are represented in `method_status.csv`, `inclusion_report.csv`, provenance, and header-complete outputs. Request-level I/O/identity/atomic-commit failure produces no completed manifest. The sanitized log closes before optional index generation; the optional index excludes itself.

## CLI contract

`scripts/evaluate.py` requires an explicit `--config PATH` in every mode and has no implicit default; the documented normal argument is `--config configs/evaluation/predictive.yaml`. `--runs-root PATH` is required in every discovery mode. `--output-root PATH` is required for evaluate, optional for completed reuse, and optional for dry-run/validate-only; when supplied in either inspection mode it is parsed only and MUST NOT be created or written. Every mode requires exactly one of `--direction`/`--both-directions` and exactly one of repeatable `--method`/`--all-methods`. `--bootstrap-seed` is required only when bootstrap/evaluate runs and is not required for dry-run, validate-only, or completed reuse. The CLI retains `--checkpoint-policy`, `--include-sensitivity`, `--bootstrap-replicates`, `--overwrite`, `--dry-run`, `--validate-only`, and optional completed `--reuse` with their specified semantics.

Conflicts:

- `--direction` with `--both-directions`; `--method` with `--all-methods`.
- `--dry-run`, `--validate-only`, and `--reuse` are pairwise exclusive.
- `--overwrite` with `--reuse`, `--dry-run`, or `--validate-only`.
- `--include-sensitivity` with a policy request that would ambiguously rename/merge analyses; it only adds separate `sensitivity_last`.
- Nonpositive bootstrap replicates, missing explicit seed for evaluate, `unsupported_method`, `unsupported_direction`, `unsupported_checkpoint_policy`, `unsupported_class_order`, target-derived checkpoint selectors, or roots that overlap/escape configured boundaries.

CLI overrides are recorded in resolved config; config and CLI may not silently broaden approved inventory. Inspection modes create no output directory. Exit categories distinguish success, validation exclusion/incompleteness, configuration error, gate block, reuse mismatch, and output failure. A static import test must prove the CLI/evaluation package has no training imports; adapters are registered explicitly rather than discovered through training registries.

## Computational summary extraction

The schema-family readers in `discovery.py` expose approved source records to the computational extractor in `report.py` for `trainable_parameter_count`, `training_runtime_seconds`, `inference_runtime_seconds`, `peak_memory_bytes`, `checkpoint_epoch`, `completed_folds`, and `completed_seeds`. Extraction applies typed/unit normalization only when an approved field and source hash exist; conflicting values are unavailable or exclusion when identity-critical. Missing fields emit null with `not_recorded`/source-aware reason, never zero. Evaluator wall/CPU time and bootstrap counts may be additional rows but never substitute for training/inference provenance.

## Dependency decision

Production directly imports NumPy, scikit-learn, SciPy (`scipy.stats.binomtest`), YAML support, and the selected PNG plotting library; therefore each must be a direct runtime dependency in `pyproject.toml` with its exact resolved version recorded in evaluation identity. SciPy cannot remain transitive or test-only.

Holm is implemented directly in `src/pada3dacb/evaluation/multiple_testing.py` from protocol v2, avoiding a production statsmodels dependency. `statsmodels` is used only by deterministic reference tests via `multipletests(..., method="holm")`; place it in the project test/dev optional dependency group, not runtime dependencies. If implementation instead imports statsmodels in production, it MUST be promoted to a direct runtime dependency and included in evaluation identity. No undeclared direct production import is allowed.

## Deterministic seams and traceability

Inject `FileSystemReader`, `HashProvider`, `Clock`, `AtomicWriter`, `LibraryVersionProvider`, and `RngFactory`; production defaults are read-only/real implementations. Core functions accept arrays and explicit RNG/seed, never global random state. Plot rendering receives canonical matrix data and deterministic metadata. Canonical JSON serialization, path sanitization, sorting, and float formatting are single shared utilities.

| Requirement | Design element / verification seam |
|---|---|
| PE-001–PE-003 | enums, configured discovery, adapter registry, provenance hydration/conflict tests |
| PE-004–PE-006 | subject-hash boundary, row validator, aggregation invariants, source-only/checkpoint rejection |
| PE-007–PE-010 | pure metrics/confusion/bootstrap/paired/Holm interfaces and library reference seams |
| PE-011, PE-014 | schema-v2 run plan in `report.py`, exact-path golden manifest, fault-injected `tables.py` atomic writer, reuse verifier |
| PE-012 | computational extractor with null/status/source hashes |
| PE-013 | parser/selector matrix and mode state-machine tests |
| PE-015 | gate service, forbidden-import check, synthetic adapter fixtures for seven methods/two directions |

Deterministic tests must eventually cover all required protocol cases, but this design phase creates no tests.

## Security, privacy, performance, rollback, observability

- **Security/privacy:** canonicalize and constrain paths; no ambient recursive discovery; open inputs read-only; never deserialize executable objects; sanitize paths; never persist raw IDs, secrets, labels/probabilities in logs, or private absolute paths. Stable subject hashes are consumed only from approved prediction exports or approved identity companion mappings and provenance-verified; evaluator-local hash generation, transformation, salting, definition, and derivation are prohibited.
- **Performance:** stream file hashing and CSV ingestion; retain only canonical numeric columns/provenance references; vectorize metrics and aggregation; process bootstrap replicates in deterministic bounded chunks while preserving RNG order; render figures after machine results. Parallelism is optional and must not alter draw order or outputs.
- **Rollback:** this phase adds an isolated package and CLI entry only. Disable/remove the entry point without changing training. Output rollback deletes only a known Phase 15 output root after external authorization; evaluator overwrite itself touches only allowlisted result paths. Protocol/schema versions prevent silent compatibility drift.
- **Observability:** UTC structured event codes for discovery counts, exclusions by stable reason, hash/provenance checks, aggregation completeness, bootstrap success/invalid counts, output staging/commit, and reuse verification. Logs expose aggregate counts and sanitized relative paths only. Manifest/status/provenance files are the audit record.

## Scope boundary

No training code or exports are changed or invoked. This design does not authorize real evaluation or results, concept evaluation, tasks, implementation, review, manuscript work, or Phase 16. Real statistics remain blocked by the named hash-bound gates.
