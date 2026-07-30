# Predictive Evaluation Specification

## Purpose

Define a read-only, publication-grade predictive evaluation capability over authorized immutable exports while preserving subjects as the statistical unit, preventing target-guided selection, protecting subject identity, and tracing every result to exact provenance.

## Requirements

### Requirement: PE-001 Approved inventory and isolation

The system MUST accept only `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, and `faster_snn`; MUST support only `adni_to_oasis` and `oasis_to_adni`; and MUST use fixed classes `CN=0,MCI=1,AD=2`. Directions and checkpoint policies MUST remain separate.

#### Scenario: Unsupported analysis axis
- GIVEN an unapproved method, direction, checkpoint policy, or class mapping
- WHEN validation runs
- THEN it MUST be excluded with `unsupported_method`, `unsupported_direction`, `unsupported_checkpoint_policy`, or `unsupported_class_order`, respectively, and no statistic

### Requirement: PE-001A Canonical candidate issue taxonomy

Candidate validation MUST use only these exact `IssueCode` tokens: `unsupported_method`, `unsupported_direction`, `unsupported_checkpoint_policy`, `unsupported_class_order`, `missing_required_field`, `unapproved_identity_mapping`, `provenance_conflict`, `input_hash_mismatch`, `target_evaluation_membership_unprovable`, `unstable_subject_identity`, `raw_identifier_persistence_attempt`, `duplicate_prediction`, `inconsistent_true_label`, `non_finite_probability`, `probability_out_of_range`, `probability_sum_invalid`, `incomplete_ensemble`, `checkpoint_policy_mismatch`, and `incompatible_subjects`. Protocol metric-unavailability reasons MUST remain a separate namespace and MUST NOT be emitted as candidate issue codes.

#### Scenario: Candidate issue serialization
- GIVEN any candidate validation defect
- WHEN status or provenance output serializes the defect
- THEN it MUST use the applicable exact canonical token and MUST NOT use an alias or metric-unavailability reason

### Requirement: PE-002 Immutable schema-family discovery

The system MUST discover only explicitly configured files under the runs root, support the shared-method and baseline-combined schema families for all seven approved adapters, compute exact-byte SHA-256, and MUST NOT modify inputs, train, or regenerate predictions.

#### Scenario: Adapter compatibility
- GIVEN one complete approved synthetic export for each method
- WHEN each adapter normalizes it
- THEN all seven MUST produce the same normalized evaluation contract

### Requirement: PE-003 Exact provenance and completeness

Inclusion MUST establish method ID, public model name, direction, source/target cohort, seed, fold, logical checkpoint, checkpoint epoch, experiment/model-configuration/training-configuration hashes, every source/target/split assignment hash including target-evaluation assignment, applicable atlas/ROI-order hashes, fixed class order, and all contributing file hashes. Missing non-identity provenance fields MAY be deterministically derived only from approved companion manifests with source hash and rule; this allowance MUST NOT apply to `subject_hash`; otherwise the candidate MUST be excluded and remain visible.

#### Scenario: Unprovable Source-Only membership
- GIVEN Source-Only target-evaluation membership cannot be proven exactly
- WHEN validation runs
- THEN Source-Only MUST fail closed with `target_evaluation_membership_unprovable`

#### Scenario: Cross-file conflict
- GIVEN any required field conflicts across rows or companions
- WHEN validation runs
- THEN the candidate MUST be excluded and conflicting values/hashes reported

### Requirement: PE-004 Subject identity and row integrity

Canonical rows MUST use a stable `subject_hash` explicitly supplied by an approved prediction export or approved identity companion mapping and MUST never expose raw identifiers. Phase 15 MUST NOT generate, transform, salt, define, or derive a subject hash. A raw identifier MAY be used transiently only to verify the supplied approved mapping. If stable cross-file identity cannot be proven, the candidate MUST be excluded with `unstable_subject_identity`. Rows MUST require finite probabilities in `[0,1]` summing to one within `1e-6`, enforce fixed-order argmax, require one consistent true label per subject across folds/seeds/methods/policies, and prohibit duplicate method/direction/seed/fold/checkpoint/role/subject rows.

#### Scenario: Raw identifier protection
- GIVEN exports contain raw subject identifiers and an approved supplied identity mapping
- WHEN identity is verified or outputs/logs are written
- THEN raw identifiers MAY be used only transiently for mapping verification and only the supplied stable `subject_hash` values MAY persist
- AND any persistence attempt MUST fail with `raw_identifier_persistence_attempt`

#### Scenario: Unstable or unapproved identity
- GIVEN the identity mapping is unapproved or stable cross-file supplied identity cannot be proven
- WHEN validation runs
- THEN the candidate MUST be excluded with `unapproved_identity_mapping` or `unstable_subject_identity`, respectively

### Requirement: PE-005 Subject-level aggregation

The system MUST enforce source OOF uniqueness; require one target prediction per subject per source fold; average target probabilities across folds within seed and then across every predeclared seed; retain per-seed diagnostics; and emit exactly one final row per subject/method/direction/policy. Partial ensembles and fold/seed pseudo-replication are forbidden.

#### Scenario: Validate-only ensemble construction
- GIVEN complete folds/seeds
- WHEN validate-only runs
- THEN it MUST construct in-memory fold and seed ensembles and validate paired alignment without computing publication statistics

### Requirement: PE-006 Checkpoint and target isolation

Primary policy MUST be `best_source_f1` under `primary_best_source_f1`; `last` MUST be separate under `sensitivity_last`. Target outcomes MUST NOT select checkpoints, epochs, methods, seeds, folds, hyperparameters, comparisons, or subsets.

#### Scenario: Target-guided selection
- GIVEN target performance favors an alternative selection
- WHEN selectors resolve
- THEN the configured source-defined policy MUST remain unchanged and the request rejected

### Requirement: PE-007 Complete metrics and unavailable values

Using float64 and explicit labels `[0,1,2]`, the system MUST compute accuracy, balanced accuracy, macro-F1, weighted F1, macro precision, macro recall, multiclass MCC, Cohen's kappa, precisely clipped multiclass log loss, unscaled multiclass Brier score, macro OVR ROC-AUC, and macro OVR average precision. Per class it MUST compute seven distinct statistical quantities—support, precision, recall/sensitivity, specificity, F1, OVR ROC-AUC, and OVR average precision—and emit eight named rows because `recall` and `sensitivity` are numerically identical aliases. Every metric MUST have value/status/reason and MUST NOT coerce undefined values to zero.

#### Scenario: Missing class or predicted positive
- GIVEN a class makes a denominator or OVR comparison undefined
- WHEN metrics run
- THEN affected values MUST be null with exact reasons while unaffected metrics remain available

### Requirement: PE-008 Matrices and publication derivation

The system MUST emit fixed-order count and row-normalized confusion CSVs and PNGs; zero-support normalized rows MUST be null/unavailable; and all publication statistics/figures MUST derive only from canonical final subject tables.

#### Scenario: Zero-support row
- GIVEN a true class has no subjects
- WHEN normalization runs
- THEN its normalized row MUST be all null with `zero_true_support`

### Requirement: PE-009 Bootstrap uncertainty

The system MUST use true-class-stratified subject bootstrap with default 10,000 replicates, explicit seed, percentile 95% intervals, linear quantiles, no invalid-replicate redraw, requested/successful/invalid counts, and minimum 95% successful replicates for an available interval.

#### Scenario: Invalid replicate
- GIVEN a resample makes a metric undefined
- WHEN summarized
- THEN it MUST count invalid, not redraw, and apply the exact availability threshold

### Requirement: PE-010 Paired inference and Holm

The system MUST use exact two-sided McNemar; paired stratified bootstrap for accuracy, balanced accuracy, macro-F1, MCC, and macro ROC-AUC; `prototype_pseudo-comparator` orientation; and Holm families of six separated by direction, policy, and statistic/metric. Inferential records with `status=available` MUST have `reason=null` and MAY carry optional informational `note_code`. For zero McNemar discordance, the system MUST emit `status=available`, `raw_p_value=1.0`, `reason=null`, and `note_code=no_discordant_pairs`. It MUST report raw/adjusted p-values and MUST NOT generate automatic all-pairs.

#### Scenario: Pair mismatch
- GIVEN subject hashes or true labels differ between methods
- WHEN paired inference is requested
- THEN the comparison MUST be unavailable without intersection-only testing

### Requirement: PE-011 Required output tree

The system MUST write directly under `<evaluation_output>` with root `evaluation_manifest.json`, `evaluation_config_resolved.yaml`, `provenance_report.json`, `method_status.csv`, `computational_summary.csv`, and `evaluation_log.txt`; MUST use `predictive/<direction>/primary_best_source_f1/` and separate `sensitivity_last/`; and MUST create the exact directories/filenames defined by `output_schema.md`, including all required metric, comparison, and four per-method confusion artifacts. It MUST NOT insert an evaluation-ID nesting layer.

#### Scenario: Completed output
- GIVEN a selected authorized synthetic evaluation
- WHEN it completes
- THEN every required exact path MUST exist and bind evaluation identity in manifests/rows

### Requirement: PE-012 Computational provenance

The system MUST extract trainable parameter count, training runtime, inference runtime, peak memory, checkpoint epoch, completed folds, and completed seeds when available. Missing values MUST be null with explicit status/reason, never zero. Evaluator timing MAY supplement but not replace these fields.

#### Scenario: Missing training runtime
- GIVEN no approved source records training runtime
- WHEN summary is written
- THEN its value MUST be null with source-aware missing status/reason

### Requirement: PE-013 Complete safe CLI

The CLI MUST implement `--config`, `--runs-root`, `--output-root`, `--direction`, `--both-directions`, `--method`, `--all-methods`, `--checkpoint-policy`, `--include-sensitivity`, `--bootstrap-replicates`, `--bootstrap-seed`, `--overwrite`, `--dry-run`, and `--validate-only` with exact semantics in `requirements.md`; optional completed `--reuse` MAY supplement them. `--config PATH` MUST be supplied in every mode and MUST have no implicit default; the documented normal value is `configs/evaluation/predictive.yaml`. `--runs-root PATH` MUST be supplied in every discovery mode. `--output-root PATH` MUST be supplied for evaluate, MAY be supplied for completed reuse, and MAY be omitted in dry-run or validate-only; if supplied in either inspection mode, it MUST NOT be created or written. Exactly one direction selector and exactly one method selector MUST be supplied in every mode. `--bootstrap-seed` MUST be supplied only when bootstrap/evaluate runs and MUST NOT be required for dry-run, validate-only, or completed reuse.

#### Scenario: Required parser inputs by mode
- GIVEN any CLI mode without `--config`, or any discovery mode without `--runs-root`, or evaluate without `--output-root` or `--bootstrap-seed`
- WHEN arguments are parsed
- THEN parsing MUST fail before discovery or scientific work
- AND no implicit configuration path or bootstrap seed MAY be substituted

#### Scenario: Dry-run and validate-only
- GIVEN either inspection mode with all required selectors and with `--output-root` omitted or supplied
- WHEN invoked
- THEN dry-run MUST discover/group/report incompleteness without metrics or outputs
- AND validate-only MUST load predictions, construct validation ensembles, and check pairing without bootstrap/publication statistics/tests/figures or persistent outputs
- AND any supplied inspection-mode output root MUST NOT be created or written

### Requirement: PE-014 Atomic outputs and completed reuse

Structured artifacts and figures MUST be atomic. Existing results MUST fail unless guarded overwrite or exact completed reuse is requested. Reuse MUST verify all identities/hashes, perform no recomputation, and write nothing.

#### Scenario: Reuse mismatch
- GIVEN any required file or identity/hash differs
- WHEN reuse runs
- THEN it MUST fail closed without mutation

### Requirement: PE-015 Gates, deterministic tests, and scope

Real evaluation MUST remain blocked until complete authorized exports, D-14-001, D-14-002, and independent protocol approval are hash-bound. Deterministic synthetic tests MUST cover all seven adapters, both directions, every metric/per-class AP, aggregation, alignment, required outputs, CLI modes, completed reuse, and prohibited behavior. The system MUST NOT change/invoke training, mix checkpoints, use target selection, perform concept evaluation/manuscript generation, create real claims, or implement Phase 16.

#### Scenario: Unresolved real-evaluation gate
- GIVEN any required gate is unresolved
- WHEN real evaluation is requested
- THEN it MUST stop before scientific statistics and name every blocking gate
