# Phase 15 Acceptance Criteria

All scenarios are mandatory, deterministic, CPU-only, and synthetic-test-only. They require no private cohort data and authorize no real result.

## Inventory, adapters, provenance, privacy

### AC-15-001 Approved inventory and directions
- GIVEN the seven approved method IDs and both directions
- WHEN dry-run groups candidates
- THEN only those methods and `adni_to_oasis,oasis_to_adni` appear in canonical order
- AND classes are `CN=0,MCI=1,AD=2`

### AC-15-002 All seven compatibility adapters
- GIVEN complete synthetic exports separately for `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, and `faster_snn`
- WHEN each adapter validates its approved schema family and companion manifests
- THEN every adapter produces the same normalized provenance and prediction contract
- AND each method has an independent passing fixture/test case

### AC-15-003 Canonical candidate issue taxonomy
- GIVEN any candidate defect
- WHEN validation records the defect
- THEN it uses exactly one applicable token from `unsupported_method`, `unsupported_direction`, `unsupported_checkpoint_policy`, `unsupported_class_order`, `missing_required_field`, `unapproved_identity_mapping`, `provenance_conflict`, `input_hash_mismatch`, `target_evaluation_membership_unprovable`, `unstable_subject_identity`, `raw_identifier_persistence_attempt`, `duplicate_prediction`, `inconsistent_true_label`, `non_finite_probability`, `probability_out_of_range`, `probability_sum_invalid`, `incomplete_ensemble`, `checkpoint_policy_mismatch`, or `incompatible_subjects`
- AND protocol metric-unavailability reasons are never used as candidate issue codes
- BUT GIVEN an unknown method
- THEN it is excluded with `unsupported_method` and no statistic

### AC-15-004 Exact provenance fields
- GIVEN a complete candidate
- WHEN validate-only runs
- THEN method ID, public name, direction, cohorts, seed, fold, logical checkpoint, checkpoint epoch, experiment/model-config/training-config hashes, every source/target/split assignment hash, applicable atlas/ROI-order hashes, class order, and source file hashes are verified and reported

### AC-15-005 Companion derivation audit
- GIVEN a field absent from prediction rows but present in an approved companion manifest
- WHEN normalization derives it
- THEN provenance records the source hash and deterministic rule
- BUT GIVEN no approved derivation
- THEN the candidate is excluded

### AC-15-006 Source-Only target membership
- GIVEN Source-Only without provable exact target-evaluation assignment hash
- WHEN validation runs
- THEN it fails closed with `target_evaluation_membership_unprovable`

### AC-15-007 Cross-file conflict and incomplete visibility
- GIVEN a conflicting identity/hash or missing expected file
- WHEN validation completes
- THEN the affected cell remains in method status and inclusion report as excluded/incomplete with evidence

### AC-15-008 Probability and duplicate rows
- GIVEN non-finite, out-of-range, non-sum-one probabilities, or duplicate method/direction/seed/fold/checkpoint/role/subject rows
- WHEN validation runs
- THEN the candidate is excluded with `non_finite_probability`, `probability_out_of_range`, `probability_sum_invalid`, or `duplicate_prediction`, respectively

### AC-15-009 Supplied-only stable subject privacy
- GIVEN a stable `subject_hash` explicitly supplied by an approved prediction export or approved identity companion mapping
- WHEN identity is normalized
- THEN Phase 15 consumes the supplied value without generating, transforming, salting, defining, or deriving a subject hash
- AND a raw identifier may be used transiently only to verify the supplied approved mapping
- BUT GIVEN an unapproved mapping
- THEN the candidate is excluded with `unapproved_identity_mapping`
- BUT GIVEN stable cross-file supplied identity cannot be proven
- THEN the candidate is excluded with `unstable_subject_identity`
- BUT GIVEN any raw identifier would persist in a result, log, figure, or error detail
- THEN processing fails with `raw_identifier_persistence_attempt` and no raw identifier is written

### AC-15-010 Consistent true labels
- GIVEN one subject hash with conflicting labels across folds, seeds, methods, or policies
- WHEN validation runs
- THEN affected evaluation/pairing fails with `inconsistent_true_label`

## Aggregation and selection

### AC-15-011 Source OOF uniqueness
- GIVEN exactly one OOF row per source subject tuple
- WHEN validated
- THEN it is eligible
- BUT GIVEN missing/duplicate OOF rows
- THEN the method-direction-policy is excluded

### AC-15-012 Fold then complete seed ensemble
- GIVEN hand-calculable probabilities for multiple folds and seeds
- WHEN validation/evaluation aggregates
- THEN fold means are computed within seed before complete-seed means
- AND exactly one final row exists per subject/method/direction/policy

### AC-15-013 Incomplete ensemble
- GIVEN any target subject missing a required fold or configured seed
- WHEN validation runs
- THEN no partial final table is eligible and the missing cell is reported

### AC-15-014 Both directions isolated
- GIVEN equivalent subject hashes in both directions
- WHEN evaluation runs
- THEN rows, metrics, comparisons, and Holm families remain direction-specific

### AC-15-015 No checkpoint mixing
- GIVEN `best_source_f1` and `last` rows
- WHEN aggregation runs
- THEN primary and sensitivity outputs are separate and no probability/statistic combines them

### AC-15-016 No target selection
- GIVEN target metrics that favor a checkpoint/method/seed/subset
- WHEN selectors are resolved
- THEN configured source-defined policy remains unchanged and target-guided selection is rejected

### AC-15-017 Fixed-order argmax tie
- GIVEN tied maximum class probabilities
- WHEN prediction is derived
- THEN the smallest fixed class index wins

## Complete metrics

### AC-15-018 Twelve aggregate metric references
- GIVEN a non-degenerate three-class float64 subject table
- WHEN metrics run
- THEN accuracy, balanced accuracy, macro-F1, weighted F1, macro precision, macro recall, multiclass MCC, Cohen's kappa, multiclass log loss, unscaled multiclass Brier score, macro OVR ROC-AUC, and macro OVR average precision match direct formulas and specified scikit-learn references

### AC-15-019 Per-class metric references
- GIVEN the same table
- WHEN per-class metrics run with labels `[0,1,2]`
- THEN seven distinct statistical quantities are computed for every class: support, precision, recall/sensitivity, specificity, F1, OVR ROC-AUC, and OVR average precision
- AND eight named rows are emitted because `recall` and `sensitivity` are numerically identical aliases
- AND all values match independent fixed-class references

### AC-15-020 Float64 and fixed labels
- GIVEN probabilities representable differently in float32
- WHEN metrics run
- THEN inputs/calculations use float64 and explicit `[0,1,2]`, never inferred labels

### AC-15-021 Exact log-loss clipping
- GIVEN zero and one probabilities in valid rows
- WHEN log loss runs
- THEN probabilities are clipped with `np.finfo(np.float64).eps`, renormalized, and passed to `log_loss(...,labels=[0,1,2],normalize=True)`
- AND the reference value matches exactly within declared float tolerance

### AC-15-022 Brier scaling
- GIVEN hand-calculable three-class probabilities
- WHEN Brier score runs
- THEN it equals mean summed squared class error with range `[0,2]`
- AND it is not divided by three

### AC-15-023 Missing true class
- GIVEN a class with zero support
- WHEN metrics run
- THEN its recall/sensitivity, OVR AUC, and OVR AP are null/unavailable
- AND dependent fixed-class macro metrics are unavailable rather than zero

### AC-15-024 No predicted positives
- GIVEN a supported class with no predicted positives
- WHEN precision runs
- THEN it is null with `no_predicted_positive`, not zero

### AC-15-025 Missing negatives and degenerate denominators
- GIVEN no one-vs-rest negative, zero MCC denominator, zero kappa denominator, or zero F1 denominator
- WHEN affected metrics run
- THEN each is null with its exact reason and unaffected metrics remain available

### AC-15-026 Confusion matrices
- GIVEN a known final subject table
- WHEN confusion outputs run
- THEN counts match fixed-label integers, supported normalized rows sum to one, and zero-support normalized rows are all null/unavailable

### AC-15-027 Publication derivation
- GIVEN contradictory cached fold/seed summaries
- WHEN metrics/tables/PNGs are generated
- THEN all values derive only from canonical final `subject_predictions/<method>.csv` and bind its hash

## Bootstrap and paired inference

### AC-15-028 Deterministic bootstrap
- GIVEN default `B=10000` and explicit seed
- WHEN bootstrap runs twice
- THEN class-stratum sizes, requested/successful/invalid counts, and 95% linear-percentile CIs are identical

### AC-15-029 Invalid replicate threshold
- GIVEN deterministic invalid metric replicates
- WHEN summarized
- THEN none are redrawn, counts are exact, and CI is available iff successful count is at least `ceil(0.95B)`

### AC-15-030 Exact McNemar
- GIVEN known paired correctness counts
- WHEN tested
- THEN p equals SciPy two-sided exact binomial McNemar with no asymptotic/continuity correction

### AC-15-031 Zero discordance
- GIVEN no discordant pairs
- WHEN McNemar runs
- THEN `status=available`, `raw_p_value=1.0`, `reason=null`, and `note_code=no_discordant_pairs`

### AC-15-032 Paired alignment
- GIVEN unequal subject-hash sets or labels
- WHEN paired inference is requested
- THEN all paired results are unavailable and no intersection-only analysis runs

### AC-15-033 Paired bootstrap metrics/orientation
- GIVEN aligned prototype/comparator rows
- WHEN paired bootstrap runs
- THEN shared stratified indices cover accuracy, balanced accuracy, macro-F1, MCC, macro ROC-AUC
- AND observed differences are `prototype_pseudo-comparator`
- AND centered plus-one p-values and percentile CIs match references

### AC-15-034 Holm exact families
- GIVEN six predeclared hypotheses including ties and an unavailable slot
- WHEN correction runs
- THEN each direction/policy/statistic family has six rows, canonical tie order, exact step-down adjusted p-values, and unavailable null slots without reducing family size

### AC-15-035 No all-pairs
- GIVEN all methods eligible
- WHEN standard comparisons run
- THEN exactly six prototype-versus-comparator tests exist per family and no other pair

## Output and computational contracts

### AC-15-036 Exact root and policy tree
- GIVEN a completed selected synthetic evaluation
- WHEN output is inspected
- THEN root contains `evaluation_manifest.json,evaluation_config_resolved.yaml,provenance_report.json,method_status.csv,computational_summary.csv,evaluation_log.txt`
- AND no unrequested evaluation-ID nesting directory exists
- AND selected trees use `predictive/<direction>/primary_best_source_f1` and separate `sensitivity_last`

### AC-15-037 Exact required directories and files
- GIVEN a selected policy tree
- WHEN output is inspected
- THEN it contains `inclusion_report.csv,subject_predictions/,metrics/,confusion_matrices/,confidence_intervals/,pairwise_comparisons/,tables/`
- AND required files include `predictive_metrics.csv,predictive_metrics_with_ci.csv,per_class_metrics.csv,pairwise_metric_differences.csv,mcnemar_results.csv`

### AC-15-038 Per-method confusion filenames
- GIVEN each selected eligible method
- WHEN figures/matrices are emitted
- THEN its directory contains exactly the required `confusion_matrix_counts.csv,confusion_matrix_normalized.csv,confusion_matrix_counts.png,confusion_matrix_normalized.png`

### AC-15-039 Computational extraction
- GIVEN manifests containing trainable parameters, training/inference runtime, peak memory, checkpoint epoch, completed folds, and completed seeds
- WHEN summary is written
- THEN values/units/source hashes are preserved
- BUT GIVEN any absent field
- THEN value is null with explicit missing status/reason, never zero

### AC-15-040 Atomic writes and input immutability
- GIVEN injected output failure and pre-run input hashes
- WHEN any mode exits
- THEN no destination contains partial bytes, temporary files are cleaned, and every input hash is unchanged

### AC-15-041 Default existing-output failure and overwrite
- GIVEN required outputs already exist
- WHEN evaluate runs without overwrite/reuse
- THEN it fails without mutation
- WHEN overwrite is explicit
- THEN only recognized Phase 15 paths under requested output root may be replaced and no run input is touched

### AC-15-042 Completed evaluation reuse
- GIVEN a completed evaluation with matching identity, config, authorization, protocol/schema, libraries, input hashes, all required paths, and artifact hashes
- WHEN `--reuse` runs
- THEN it succeeds without recomputation or writes
- BUT GIVEN any mismatch or incomplete output
- THEN reuse fails closed

## CLI modes and boundaries

### AC-15-043 Complete flag parsing
- GIVEN valid combinations of `--config,--runs-root,--output-root,--direction/--both-directions,--method/--all-methods,--checkpoint-policy,--include-sensitivity,--bootstrap-replicates,--bootstrap-seed,--overwrite,--dry-run,--validate-only` and optional `--reuse`
- WHEN parsed
- THEN `--config PATH` is required in every mode with no implicit default and the documented normal value is `configs/evaluation/predictive.yaml`
- AND `--runs-root PATH` is required in every discovery mode
- AND evaluate requires `--output-root PATH` and `--bootstrap-seed INTEGER`
- AND completed reuse may omit `--output-root` and does not require `--bootstrap-seed`
- AND dry-run and validate-only may omit `--output-root` and do not require `--bootstrap-seed`
- AND exactly one direction selector and exactly one method selector are required in every mode
- AND every remaining flag has the specified selection/mutual-exclusion semantics
- AND missing required arguments or invalid combinations fail before discovery or scientific work without substituting a config path or bootstrap seed

### AC-15-043A Inspection output-root is non-writing
- GIVEN dry-run or validate-only with an explicit `--output-root PATH` that does not exist
- WHEN the inspection completes or fails validation
- THEN the supplied path is not created
- AND no file or directory is written beneath it

### AC-15-044 Dry-run
- GIVEN complete and incomplete configured candidates
- WHEN `--dry-run` runs
- THEN it discovers candidates, validates intended grouping, and reports incomplete methods/gates
- AND computes no metric and creates no result artifact

### AC-15-045 Validate-only aggregation/alignment
- GIVEN valid prediction rows across folds/seeds and two pairable methods
- WHEN `--validate-only` runs
- THEN it loads/validates rows, constructs in-memory fold and complete-seed subject ensembles, and validates paired subject/label alignment
- AND performs no bootstrap, publication metric/test, figure, or persistent result write

### AC-15-046 Real gate
- GIVEN real exports without complete authorization, D-14-001, D-14-002, or independent protocol approval
- WHEN evaluate is requested
- THEN it stops before scientific statistics and reports every blocking gate

### AC-15-047 No training invocation
- GIVEN spies on all training and prediction-generation entry points
- WHEN every CLI mode runs
- THEN none is invoked

### AC-15-048 No prohibited/later work
- GIVEN repository and output inspection after the phase/test workflow
- WHEN scope is audited
- THEN no checkpoint mixing, target selection, training change/invocation, concept evaluation, intervention, manuscript generation, real result, scientific claim, or Phase 16 artifact/behavior exists
