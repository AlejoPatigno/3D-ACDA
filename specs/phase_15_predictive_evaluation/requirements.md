# Phase 15 Predictive Evaluation Requirements

## Contract

Phase 15 is read-only evaluation of immutable prediction exports. Approved method IDs are `source_only,coral,mmd,cdan,prototype_pseudo,aagn,faster_snn`; directions are `adni_to_oasis,oasis_to_adni`; classes are fixed `CN=0,MCI=1,AD=2`. Normative statistics are in `statistical_protocol.md`, files in `output_schema.md`, and tests in `acceptance.md`.

### Normative candidate issue taxonomy

Candidate validation MUST use only the following exact `IssueCode` tokens. Protocol metric-unavailability reasons form a separate namespace and MUST NOT be emitted as candidate issue codes.

| IssueCode | Candidate defect |
|---|---|
| `unsupported_method` | Method is outside the approved inventory. |
| `unsupported_direction` | Direction is outside the approved inventory. |
| `unsupported_checkpoint_policy` | Checkpoint policy is outside the approved inventory. |
| `unsupported_class_order` | Class order differs from `CN=0,MCI=1,AD=2`. |
| `missing_required_field` | A required field has no approved source. |
| `unapproved_identity_mapping` | A subject identity mapping is not explicitly approved. |
| `provenance_conflict` | Required provenance values conflict across sources. |
| `input_hash_mismatch` | Exact input bytes do not match the declared hash. |
| `target_evaluation_membership_unprovable` | Exact target-evaluation membership cannot be proven. |
| `unstable_subject_identity` | Stable cross-file supplied `subject_hash` identity cannot be proven. |
| `raw_identifier_persistence_attempt` | A raw identifier would enter persistent output, logs, figures, or errors. |
| `duplicate_prediction` | A canonical prediction key occurs more than once. |
| `inconsistent_true_label` | A subject has conflicting true labels. |
| `non_finite_probability` | A probability is not finite. |
| `probability_out_of_range` | A probability is outside `[0,1]`. |
| `probability_sum_invalid` | A probability row does not sum to one within `1e-6`. |
| `incomplete_ensemble` | A required fold or seed prediction is absent. |
| `checkpoint_policy_mismatch` | Candidate checkpoint data do not match the selected policy. |
| `incompatible_subjects` | Paired candidates do not have identical ordered subjects and labels. |

## Inputs and provenance

### REQ-15-001 Immutable configured discovery

The evaluator MUST discover only configured candidates under `--runs-root`, MUST support the shared-method family for Source-Only/CORAL/MMD/CDAN/prototype_pseudo and baseline combined family for AAGN/FasterSNN, and MUST compute exact-byte SHA-256 for every prediction and companion manifest/fold-result file. It MUST NOT mutate inputs, search outside configured roots, silently remap paths, train, or regenerate predictions.

### REQ-15-002 Exact normalized provenance

For every method/direction/seed/fold/logical checkpoint, inclusion MUST establish without conflict:

- method ID and public model name;
- direction and source/target cohort;
- seed and fold;
- logical checkpoint and checkpoint epoch;
- experiment hash, model configuration hash, and training configuration hash;
- source subject, source-train, source-validation, target subject, target-adaptation, target-evaluation, and split assignment hashes;
- atlas and ROI-order hashes when applicable, or approved evidence of `not_applicable`;
- fixed class order;
- exact hashes of all files providing or deriving these fields.

A non-identity provenance field MUST come directly from its schema family or MAY be deterministically and audibly derived from approved companion manifests, recording source file hash and derivation rule; this allowance MUST NOT apply to `subject_hash`. An absent, conflicting, or unprovable required value MUST exclude the candidate. Source-Only MUST fail closed if exact target-evaluation membership and `target_evaluation_assignment_hash` cannot be proven.

### REQ-15-003 Prediction identity and privacy

Probabilities MUST be float64-compatible, finite, each in `[0,1]`, and sum to one within absolute tolerance `1e-6`. Predicted label MUST be fixed-order argmax. For each stable `subject_hash`, true label MUST be singular and consistent across folds, seeds, methods, and policies in a direction. Duplicate `(method,direction,seed,fold,logical checkpoint,prediction role,subject_hash)` rows are forbidden.

Canonical evaluation and publication artifacts MUST use a stable `subject_hash` explicitly supplied by an approved prediction export or approved identity companion mapping, never raw `subject_id`. Phase 15 MUST NOT generate, transform, salt, define, or derive a subject hash. A raw identifier MAY be used transiently only to verify the supplied approved mapping and MUST be discarded immediately afterward. An unapproved mapping MUST exclude the candidate with `unapproved_identity_mapping`; inability to prove stable cross-file identity MUST exclude it with `unstable_subject_identity`; and any attempted persistence of a raw identifier MUST fail with `raw_identifier_persistence_attempt`.

### REQ-15-004 Completeness and compatibility visibility

The resolved configuration MUST predeclare expected methods, directions, folds, seeds, checkpoint policies, and roles. Every expected cell, including missing cells, MUST appear in `method_status.csv` and policy `inclusion_report.csv` with status and reason. Incomplete/incompatible methods MUST be excluded fail-closed, never hidden.

All seven method adapters MUST normalize to the same contract. Paired methods MUST have identical ordered final `subject_hash` sets and true labels, direction, target cohort, checkpoint policy, complete seed ensemble, class order, and assignment hashes. Intersection-only comparison is forbidden.

## Aggregation and selection

### REQ-15-005 Subject statistical unit

Source OOF MUST contain exactly one row per source subject/method/direction/seed/logical checkpoint across folds. Target data MUST contain exactly one row per target subject for each predeclared source fold. Target class probabilities MUST be averaged across folds within seed, per-seed rows/metrics retained as diagnostics, then averaged across the complete predeclared seed ensemble. Exactly one final row per target subject/method/direction/policy MUST result. Folds, seeds, directions, and policies MUST NOT be treated as independent subjects or pooled.

### REQ-15-006 Checkpoint and target isolation

Primary policy MUST be `best_source_f1`; sensitivity MUST be separate `last`, under directory `sensitivity_last`. Target outcomes MUST NOT select checkpoints, epochs, methods, seeds, folds, hyperparameters, comparisons, or subsets. D-14-002 MUST NOT be retrospectively resolved from evaluation.

## Statistics

### REQ-15-007 Complete metrics

Using float64 and fixed labels, the evaluator MUST compute every aggregate metric defined in the protocol: accuracy, balanced accuracy, macro-F1, weighted F1, macro precision, macro recall, multiclass MCC, Cohen's kappa, multiclass log loss, unscaled multiclass Brier score, macro OVR ROC-AUC, and macro OVR average precision.

Per class the evaluator MUST compute seven distinct statistical quantities—support, precision, recall/sensitivity, specificity, F1, OVR ROC-AUC, and OVR average precision—and MUST emit eight named rows because `recall` and `sensitivity` are numerically identical aliases. It MUST implement exact clipping/renormalization for log loss, explicit availability and reason rules, and MUST NOT replace undefined values with zero.

### REQ-15-008 Matrices and uncertainty

The evaluator MUST produce fixed-order count and true-row-normalized confusion matrices; zero-support normalized rows MUST be null/unavailable. Every publication table and figure MUST derive only from canonical final subject tables.

Bootstrap MUST be true-class-stratified by subject, default 10,000 replicates, explicit seed, percentile 95% CI, NumPy linear quantiles, no redraw of invalid replicates, explicit requested/successful/invalid counts, and CI availability threshold `successful>=ceil(0.95*requested)`.

### REQ-15-009 Paired inference and Holm

Exactly six comparisons are predeclared: `prototype_pseudo` versus each other approved method. Exact two-sided McNemar MUST use the protocol contingency and binomial p-value. With zero discordant pairs, McNemar MUST emit `status=available`, `raw_p_value=1.0`, `reason=null`, and `note_code=no_discordant_pairs`. Paired stratified bootstrap MUST cover accuracy, balanced accuracy, macro-F1, MCC, and macro ROC-AUC using shared subject indices and `prototype_pseudo-comparator` orientation. Holm families MUST retain size six and be separate by direction, checkpoint policy, and statistic/metric. Raw and adjusted p-values MUST be emitted. No automatic all-pairs.

## Required output

### REQ-15-010 Tree and filenames

Evaluate mode MUST write directly under `<evaluation_output>` with no inserted evaluation-ID directory. It MUST create root `evaluation_manifest.json`, `evaluation_config_resolved.yaml`, `provenance_report.json`, `method_status.csv`, `computational_summary.csv`, and `evaluation_log.txt`.

Selected analyses MUST be under `predictive/<direction>/primary_best_source_f1/` and, separately, `predictive/<direction>/sensitivity_last/`. Each selected policy tree MUST contain `inclusion_report.csv` and directories `subject_predictions/`, `metrics/`, `confusion_matrices/`, `confidence_intervals/`, `pairwise_comparisons/`, and `tables/`.

Required exact machine/publication filenames are `predictive_metrics.csv`, `predictive_metrics_with_ci.csv`, `per_class_metrics.csv`, `pairwise_metric_differences.csv`, `mcnemar_results.csv`, `method_status.csv`, and `computational_summary.csv`. For each selected method/direction/policy, exact confusion filenames are `confusion_matrix_counts.csv`, `confusion_matrix_normalized.csv`, `confusion_matrix_counts.png`, and `confusion_matrix_normalized.png`. Extra indexes MAY supplement but MUST NOT replace these paths.

### REQ-15-011 Output integrity and reuse

Every output MUST carry/inherit schema/protocol version, evaluation identity, direction, policy, method, status, reasons, config/input hashes, and library versions. Structured/PNG writes MUST use same-filesystem temporary files and atomic replacement. Existing results fail by default. Overwrite MUST be confined to recognized Phase 15 outputs under requested root. Completed reuse MUST verify evaluation identity and every config, authorization, protocol/schema, library, input, required-file, and index hash; it MUST perform no recomputation or write.

### REQ-15-012 Computational summary

For every method/direction/policy, computational summary MUST extract when available: trainable parameter count, training runtime, inference runtime, peak memory, checkpoint epoch, completed folds, and completed seeds. Each field MUST have value, unit, status, reason, and source hash. Missing data MUST be null with explicit `unavailable`/`not_recorded`; zero MUST not mean missing. Evaluator wall/CPU time and bootstrap counts MAY be additional.

## CLI and modes

### REQ-15-013 Complete CLI

CLI MUST support all flags:

- `--config PATH` required in every mode, with no implicit default; the documented normal value is `configs/evaluation/predictive.yaml`;
- `--runs-root PATH` required in every discovery mode;
- `--output-root PATH` required for evaluate, optional for completed reuse, and optional/non-writing in dry-run and validate-only; if supplied in either inspection mode, the path MUST NOT be created or written;
- exactly one of `--direction {adni_to_oasis,oasis_to_adni}` or `--both-directions` in every mode;
- exactly one or more `--method {approved_id}` or `--all-methods` in every mode;
- `--checkpoint-policy {best_source_f1,last}` (default `best_source_f1`);
- `--include-sensitivity`, which adds separate `last` when primary is selected and is invalid with checkpoint policy `last`;
- `--bootstrap-replicates INTEGER` default `10000`;
- `--bootstrap-seed INTEGER` required only when bootstrap/evaluate runs and not required for dry-run, validate-only, or completed reuse;
- `--overwrite`;
- mutually exclusive `--dry-run` and `--validate-only`;
- optional `--reuse`, mutually exclusive with overwrite and inspection modes.

Selectors MUST filter only predeclared analyses; target outcomes MUST never drive them. Missing mode-required arguments MUST fail during parsing before discovery or scientific work.

### REQ-15-014 Dry-run and validate-only

Dry-run MUST discover configured candidates, validate intended method/direction/seed/fold/checkpoint grouping from configuration and metadata, report incomplete methods and gates, calculate no metrics, and create no result artifacts.

Validate-only MUST load and validate prediction rows and provenance, construct subject-level fold ensembles and complete predeclared seed ensembles as needed to validate uniqueness/completeness, construct canonical in-memory final subject tables, and validate paired subject/label alignment. It MUST perform no bootstrap, publication metrics/tests, figures, or persistent result artifacts.

No mode MAY invoke training, prediction regeneration, concept evaluation, manuscript generation, or Phase 16.

## Gates, tests, boundaries

### REQ-15-015 Real-evaluation gate

Real evaluation MUST stop before scientific statistics until complete authorized exports, maintainer resolutions D-14-001 and D-14-002, and independent statistical-protocol approval are hash-bound. Synthetic fixtures alone MAY exercise implementation and MUST be labeled test-only.

### REQ-15-016 Deterministic minimum tests

CPU-only deterministic tests MUST cover every scenario in `acceptance.md`, including every metric, every per-class metric/AP, each of seven adapters, both directions, provenance and privacy, aggregation/alignment, checkpoint isolation, output names/tree, modes, completed reuse, and all prohibited behavior.

### REQ-15-017 Scope boundary

Phase 15 MUST NOT change training, models, losses, schedules, checkpoints, splits, preprocessing, concepts, immutable exports, or experiment hashes; MUST NOT invoke training, perform target-guided selection, concept evaluation, manuscript generation, publication, or Phase 16; and MUST NOT create real results or claims during this phase.
