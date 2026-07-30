# Phase 15 Output Schema

## Schema identity

`schema_version: phase15-output-v2`

For evaluate, `<evaluation_output>` is exactly the required path selected by `--output-root`; no evaluation-ID directory is inserted. Completed reuse MAY accept `--output-root`. Dry-run and validate-only MAY accept `--output-root`, but the supplied path is non-writing and MUST NOT be created. Evaluation identity is a lowercase SHA-256 over canonical configuration, protocol/schema versions, exact library versions, and ordered input hashes, stored in manifests and rows.

## Required tree

```text
<evaluation_output>/
├── evaluation_manifest.json
├── evaluation_config_resolved.yaml
├── provenance_report.json
├── method_status.csv
├── computational_summary.csv
├── evaluation_log.txt
├── artifact_index.json                         # optional extension; never replaces required files
└── predictive/
    ├── adni_to_oasis/
    │   ├── primary_best_source_f1/
    │   │   ├── inclusion_report.csv
    │   │   ├── subject_predictions/
    │   │   │   ├── source_only.csv
    │   │   │   ├── coral.csv
    │   │   │   ├── mmd.csv
    │   │   │   ├── cdan.csv
    │   │   │   ├── prototype_pseudo.csv
    │   │   │   ├── aagn.csv
    │   │   │   └── faster_snn.csv
    │   │   ├── metrics/
    │   │   │   ├── predictive_metrics.csv
    │   │   │   └── per_class_metrics.csv
    │   │   ├── confusion_matrices/<method>/
    │   │   │   ├── confusion_matrix_counts.csv
    │   │   │   ├── confusion_matrix_normalized.csv
    │   │   │   ├── confusion_matrix_counts.png
    │   │   │   └── confusion_matrix_normalized.png
    │   │   ├── confidence_intervals/
    │   │   │   └── predictive_metrics_with_ci.csv
    │   │   ├── pairwise_comparisons/
    │   │   │   ├── pairwise_metric_differences.csv
    │   │   │   ├── mcnemar_results.csv
    │   │   │   └── holm_adjusted.csv
    │   │   └── tables/
    │   │       └── predictive_metrics_with_ci.csv
    │   └── sensitivity_last/                   # same required contents
    └── oasis_to_adni/                          # same policy trees
```

Only requested directions/methods/policies need scientific rows, but required root files and selected policy-tree files MUST exist. Excluded/incomplete selected methods remain in root `method_status.csv`, policy `inclusion_report.csv`, and header-complete outputs. Sensitivity tree is created only when `last` is selected or `--include-sensitivity` is set.

## Privacy and common representation

Canonical and publication rows MUST use a stable `subject_hash` explicitly supplied by an approved prediction export or approved identity companion mapping; raw `subject_id` MUST NOT be written to any Phase 15 result, log, figure metadata, or error detail. Phase 15 MUST NOT generate, transform, salt, define, or derive a subject hash. Internal transient raw identifiers MAY be used only to verify the supplied approved mapping and MUST be discarded immediately. An unapproved mapping is `unapproved_identity_mapping`; inability to prove stable cross-file supplied identity is `unstable_subject_identity`; attempted raw-ID persistence is `raw_identifier_persistence_attempt`.

All rows carry or inherit `schema_version,protocol_version,evaluation_identity,analysis_mode,direction,checkpoint_policy,method_id,status,reason`. Metric and inferential records MUST have `reason=null` when `status=available`; inferential records MAY additionally carry an optional informational `note_code`. CSV is UTF-8, RFC 4180, LF, fixed columns/order, round-trip float decimals, and empty field for null. JSON/YAML use null. Publication rounding occurs only in `tables/` and PNG labels.

## Normative candidate issue taxonomy

Candidate issue fields MUST use only these exact tokens; protocol metric-unavailability reasons are a separate namespace and MUST NOT appear as candidate issue codes.

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

## Root files

### `evaluation_manifest.json`

Required: schema/protocol versions; evaluation identity; real/synthetic mode; created UTC metadata; selected methods/directions/policies; fixed classes; bootstrap count/seed/CI policy; configuration hash; authorization hash and gate states including D-14-001/D-14-002/protocol approval; library versions; ordered input/output hash references; overwrite/reuse disposition.

### `evaluation_config_resolved.yaml`

The fully resolved, path-normalized evaluation configuration, including requested CLI selectors, expected folds/seeds, schema-family adapter per method, and hashes. It MUST contain no private hashing secret or raw subject identifier.

### `provenance_report.json`

For every expected file/candidate, record path in sanitized configured-root-relative form, exact-byte SHA-256, size, schema family/version, each required provenance field and its source (`row`, `run_manifest`, `fold_result`, approved companion), derivation rule if any, equality checks, issues, status, and reason. Missing/unprovable values remain explicit.

### `method_status.csv`

Columns: `schema_version,evaluation_identity,method_id,public_model_name,direction,checkpoint_policy,expected_folds,completed_folds,expected_seeds,completed_seeds,status,reason_code,reason_detail`.

### `computational_summary.csv`

Columns: `schema_version,evaluation_identity,method_id,direction,checkpoint_policy,field,value,unit,status,reason,source_file_sha256`. Required fields per method are `trainable_parameter_count,training_runtime_seconds,inference_runtime_seconds,peak_memory_bytes,checkpoint_epoch,completed_folds,completed_seeds`. Additional fields MAY include evaluator wall/CPU time and bootstrap counts. Missing values MUST be null with `unavailable` or `not_recorded` and reason, never zero.

### `evaluation_log.txt`

UTF-8 UTC line log with level, stable event code, evaluation identity, and sanitized message. It MUST NOT contain raw subject identifiers, subject labels/probabilities, private absolute paths, or secrets.

## Policy files

### `inclusion_report.csv`

Columns: `schema_version,evaluation_identity,method_id,public_model_name,direction,checkpoint_policy,seed,fold,prediction_role,expected,present,provenance_valid,identity_valid,probability_valid,complete,status,reason_code,reason_detail,input_sha256s`.

### `subject_predictions/<method>.csv`

One final row per subject. Columns: `schema_version,protocol_version,evaluation_identity,analysis_mode,direction,checkpoint_policy,method_id,public_model_name,subject_hash,true_label,prob_cn,prob_mci,prob_ad,predicted_label,fold_count,seed_count,source_file_sha256s,status,reason`. Sort by `subject_hash`. Raw IDs are forbidden. These files are the sole source for metrics, comparisons, tables, and figures.

### `metrics/predictive_metrics.csv`

Columns: common fields plus `metric,value,status,reason,subject_count`. Exactly these aggregate metrics per included method: `accuracy,balanced_accuracy,macro_f1,weighted_f1,macro_precision,macro_recall,multiclass_mcc,cohen_kappa,multiclass_log_loss,multiclass_brier_score,macro_ovr_roc_auc,macro_ovr_average_precision`.

### `metrics/per_class_metrics.csv`

Columns: common fields plus `class_label,class_index,support,metric,value,status,reason`. The evaluator MUST compute seven distinct statistical quantities and emit exactly eight named rows: `support,precision,recall,sensitivity,specificity,f1,ovr_roc_auc,ovr_average_precision`, because `recall` and `sensitivity` are numerically identical aliases.

### `confidence_intervals/predictive_metrics_with_ci.csv`

Columns: common fields plus `metric,point_estimate,ci_level,ci_method,ci_low,ci_high,bootstrap_seed,requested,successful,invalid,status,reason`. Contains every aggregate metric.

### `pairwise_comparisons/pairwise_metric_differences.csv`

Columns: `schema_version,protocol_version,evaluation_identity,direction,checkpoint_policy,reference_method,comparator_method,metric,orientation,observed_difference,ci_level,ci_method,ci_low,ci_high,p_value_method,raw_p_value,adjusted_p_value,bootstrap_seed,requested,successful,invalid,status,reason,reference_subject_table_sha256,comparator_subject_table_sha256`.

### `pairwise_comparisons/mcnemar_results.csv`

Columns: common comparison identity plus `n_subjects,n00_both_wrong,n01_reference_correct,n10_comparator_correct,n11_both_correct,discordant_count,test,raw_p_value,adjusted_p_value,status,reason,note_code`. Test is `exact_two_sided_mcnemar`; reference is `prototype_pseudo`. When `discordant_count=0`, the exact row MUST contain `status=available`, `raw_p_value=1.0`, `reason=null`, and `note_code=no_discordant_pairs`. Other available McNemar rows MUST have `reason=null` and an empty/null `note_code` unless another protocol-defined informational note applies.

### `pairwise_comparisons/holm_adjusted.csv`

Columns: `schema_version,protocol_version,evaluation_identity,direction,checkpoint_policy,family_id,statistic_family,metric,family_size,available_count,reference_method,comparator_method,raw_p_value,holm_rank,adjusted_p_value,status,reason`. Exactly six rows per family; family size is six.

### Confusion files

Each `confusion_matrices/<method>/` contains all four exact filenames. CSV columns are `true_class,true_class_index,row_status,row_reason,pred_cn,pred_mci,pred_ad`; count cells are integers, normalized zero-support rows are null. PNGs MUST identify count versus row-normalized content, fixed labels, direction, policy, method, evaluation identity, and source subject-table SHA-256.

### `tables/predictive_metrics_with_ci.csv`

Publication-formatted copy derived only from the exact subject tables and machine metrics/CI files. It MUST retain status/reason and subject-table hashes and MUST not be the source of machine inference.

## Exact provenance fields

For every included method/direction/seed/fold/logical checkpoint, provenance MUST establish:

`method_id,public_model_name,direction,source_cohort,target_cohort,seed,fold,logical_checkpoint,checkpoint_epoch,experiment_hash,model_configuration_hash,training_configuration_hash,source_subject_assignment_hash,source_train_assignment_hash,source_validation_assignment_hash,target_subject_assignment_hash,target_adaptation_assignment_hash,target_evaluation_assignment_hash,split_assignment_hash,atlas_hash,roi_order_hash,class_order`.

`atlas_hash` and `roi_order_hash` MAY be `not_applicable` only when the approved method contract proves they do not apply; absence is not equivalent. Every non-identity provenance field must be present in the schema family or deterministically and audibly derived from approved companion manifests with source hash and rule; this allowance MUST NOT apply to `subject_hash`. Otherwise exclude. In particular, Source-Only target-evaluation membership MUST be proven by `target_evaluation_assignment_hash`; if it cannot be established, Source-Only fails closed.

Prediction validation additionally requires finite/sum-one probabilities, one true label per `subject_hash` consistent across folds/seeds, and no duplicate `(method_id,direction,seed,fold,logical_checkpoint,prediction_role,subject_hash)` rows.

## Writes, overwrite, and reuse

Required JSON, YAML, CSV, and PNG files MUST use same-filesystem temporary siblings, flush/close, then atomic replace. The log closes before optional `artifact_index.json`, which may hash all required artifacts and exclude itself.

Existing selected result paths fail without `--overwrite` or `--reuse`. `--overwrite` MUST replace only recognized Phase 15 result files beneath the exact requested output root and MUST never touch runs/inputs. `--reuse` is read-only and succeeds only for a completed evaluation whose evaluation identity, config, authorization, protocol/schema, library, input, required-file, and optional index hashes all verify. Reuse MUST not recompute metrics or rewrite any artifact.

Dry-run and validate-only create no persistent result artifacts and MUST NOT create or write a supplied `--output-root`.
