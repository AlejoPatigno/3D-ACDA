# Phase 16 — Quantitative Concept, Anatomical Consistency, Head Agreement and ROI Stability Evaluation

## Requirements

### Scope

Phase 16 evaluates the interpretability outputs of the approved PADA-3DACB family without changing training.

**Eligible methods** (have concept heads):
- `source_only`
- `coral`
- `mmd`
- `cdan`
- `prototype_pseudo`

**Not applicable to concept evaluation** (no PADA-3DACB concept head):
- `aagn`
- `faster_snn`

AAGN and FasterSNN must be reported as:
- `not_applicable_no_pada3dacb_concept_head`

They must not be treated as failed or incomplete methods.

### Regression-protected behavior

The following must remain unchanged:
- preprocessing
- artifact precomputation
- data partitions
- PADA-3DACB architecture
- source core losses
- Source-Only, CORAL, MMD, CDAN, prototype_pseudo
- AAGN, FasterSNN
- Phase 15 predictive evaluation

### Phase 16 forbidden behaviors

- concept interventions
- causal claims
- ROI deletion or retraining experiments
- architecture ablations
- manuscript rewriting
- new training runs
- real ADNI/OASIS evaluation
- Phase 17 production work

### Functional requirements

**FR-01**: Extract concept and anatomy tensors from frozen PADA-3DACB checkpoints
- Load checkpoints in no-grad mode
- Run forward pass on source validation and target evaluation subjects
- Extract: concepts, c_target, g_bar, alpha, latent_logits, concept_logits, latent probabilities, concept-head probabilities

**FR-02**: Implement subject-level output contract
For every evaluated subject, export:
- method, model, direction, source_domain, target_domain
- seed, fold, logical_checkpoint, checkpoint_epoch, experiment_hash
- subject_id, subject_hash, cohort, true_label, label_name
- predicted_concepts, concept_targets, anatomical_targets
- attention_alpha, latent_probabilities, concept_probabilities
- latent_prediction, concept_prediction

Vector fields must have exactly K entries in canonical ROI order.

**FR-03**: Implement fold and seed aggregation
- Source validation: true out-of-fold predictions, each source subject once per method/seed
- Target evaluation: average predicted concepts across folds; average latent/concept probabilities across folds; average attention alpha across folds as descriptive profile; preserve c_target and g_bar as immutable; produce one fold-ensemble record per target subject
- Multiple seeds: aggregate folds within seed first; retain per-seed records; optionally average per-seed outputs into predeclared final subject record
- Do not count repeated fold/seed predictions as independent subjects
- Do not pool transfer directions

**FR-04**: Implement concept fidelity metrics (c_hat vs c_target)
Global: MAE, RMSE, mean signed bias
Per subject: MAE across ROIs, RMSE across ROIs
Per ROI across subjects: MAE, RMSE, mean signed bias, Pearson correlation, Spearman correlation
Correlations must return availability status and reason when ROI is constant, sample count insufficient, or numerical evaluation undefined. Do not replace undefined correlations with zero.

**FR-05**: Implement anatomical consistency metrics (c_hat vs g_bar)
Same structure as FR-04: global MAE/RMSE/bias, per-subject MAE/RMSE, per-ROI MAE/RMSE/Pearson/Spearman
Report separately: unweighted descriptive anatomy agreement, canonical weighted anatomy score
Do not merge into one undocumented value. Do not claim agreement with g_bar proves causal/pathological validity.

**FR-06**: Implement latent and concept-head agreement
- Latent-head predictive metrics
- Concept-head predictive metrics
- Top-1 agreement rate, top-1 disagreement rate
- Mean Jensen-Shannon divergence
- Canonical consistency-loss direction derived from L_cons
- Per-class disagreement counts
- Keep predictive accuracy separate from concept fidelity

**FR-07**: Implement ROI-level stability
Per-ROI concept fidelity profiles, anatomy-consistency profiles, mean predicted concept profiles, mean attention-alpha profiles
Across folds and seeds: pairwise Spearman rank correlation, mean pairwise rank correlation, standard deviation across model instances, top-k Jaccard overlap for explicit configured k values, ROI rank dispersion
Real-run top-k values must be explicit in configuration; synthetic fixtures may use small test-only values
Do not call attention alpha a causal importance score. Use terminology: attention profile, concept profile, ROI stability. Do not use: causal importance, biomarker, disease mechanism.

**FR-08**: Implement class-conditional descriptive profiles
Separately for CN, MCI, AD:
- Mean predicted concept per ROI, mean c_target per ROI, mean g_bar per ROI
- Bootstrap confidence intervals over subjects, class support
- Do not conduct unrestricted ROI-by-ROI significance testing by default
- Inferential class comparisons must be separately predeclared with multiplicity correction

**FR-09**: Implement method comparisons
Primary comparisons: prototype_pseudo vs {source_only, coral, mmd, cdan}
Use paired subjects. Compare at minimum: per-subject concept MAE, per-subject anatomy MAE, latent/concept-head JS divergence
Use paired stratified subject bootstrap and Holm correction by direction, checkpoint policy, metric family
Do not compare PADA concept metrics against AAGN or FasterSNN
Do not use target results to select method or checkpoint

**FR-10**: Generate figures and tables
Required machine-readable tables: concept_fidelity_global.csv, concept_fidelity_per_subject.csv, concept_fidelity_per_roi.csv, anatomy_consistency_global.csv, anatomy_consistency_per_subject.csv, anatomy_consistency_per_roi.csv, head_agreement.csv, roi_stability.csv, class_conditional_profiles.csv, paired_method_comparisons.csv, method_status.csv
Required figures: concept_fidelity_roi_heatmap.png, anatomy_consistency_roi_heatmap.png, head_agreement_matrix.png, roi_stability_heatmap.png, class_conditional_concept_profiles.png
Use fixed ROI ordering. Do not automatically select only most favorable ROIs. Any reduced top-k figure must use predeclared rule and retain complete machine-readable table. No causal intervention figures.

**FR-11**: Confidence intervals
Reuse Phase 15 subject-level bootstrap infrastructure
Default: 95% confidence, 10,000 replicates, subject resampling unit, diagnosis class stratification, explicit seed
Track: requested/successful/invalid replicates, unavailable metrics, bootstrap seed
Do not bootstrap ROI entries as independent subjects. Do not bootstrap repeated fold outputs before subject-level aggregation.

**FR-12**: Provenance and real-run gate
Validate: method, model, direction, seed, fold, checkpoint, experiment hash, split hashes, atlas hash, ROI-order hash, concept-normalizer hash, artifact assignment, model configuration hash, evaluation authorization
Real evaluation config must contain explicit expected hashes and `authorized: false` by default
Real run must fail while authorization is false or required hashes are null
Synthetic validation must be clearly marked fixture-only
Do not evaluate outputs from incompatible concept normalizers or ROI orders

### CLI requirements

**FR-13**: Implement CLI
```
python scripts/evaluate_concepts.py \
  --config configs/evaluation/concepts.yaml \
  --runs-root <runs> \
  --artifact-root <artifacts> \
  --output-root <results> \
  --direction ADNI_to_OASIS \
  --checkpoint-policy best_source_f1
```

Support: --config, --runs-root, --artifact-root, --output-root, --direction, --both-directions, --method, --all-pada-methods, --checkpoint-policy, --include-sensitivity, --bootstrap-replicates, --bootstrap-seed, --top-k, --device, --overwrite, --dry-run, --validate-only

**FR-14**: Dry-run behavior
- Discover checkpoints and artifacts
- Validate intended groupings and hashes
- Report missing methods
- Report AAGN/FasterSNN as not applicable
- Perform no model forward
- Create no result artifacts

**FR-15**: Validate-only behavior
- Construct read-only evaluation dataset
- Load one checkpoint
- Run one no-grad batch
- Validate tensor dimensions and ROI order
- Construct no bootstrap outputs
- Generate no publication figures
- Perform no parameter update

The CLI must never invoke training.

### Non-functional requirements

**NFR-01**: Deterministic CPU-only execution by default
**NFR-02**: CUDA-specific tests optional
**NFR-03**: Synthetic fixtures small and deterministic
**NFR-04**: No real ADNI/OASIS data required in CI
**NFR-05**: Do not weaken tolerances only to make tests pass
**NFR-06**: Document tolerance choices
**NFR-07**: Exact algebraic operations use exact equality where feasible
**NFR-08**: Float32 model comparisons use explicit rtol/atol
**NFR-09**: Interrupted/resumed runs match uninterrupted runs exactly when runtime contract supports it

### Exclusions

- No concept interventions
- No causal claims
- No ROI deletion/retraining experiments
- No architecture ablations
- No manuscript rewriting
- No new training runs
- No real ADNI/OASIS evaluation
- No Phase 17 production work

### Manuscript scores

For each named score (CFS, ACS, PCS, QIS):
- Record exact equation
- Record source
- Record required inputs
- Record reduction and normalization
- Distinguish loss from posthoc score
- Mark BLOCKED when equation incomplete or ambiguous
- Do not invent definitions merely from names

## Acceptance criteria

See `acceptance.md` for executable acceptance criteria.

## Decisions

See `decisions.md` for resolved ambiguities and deliberate differences from historical notebooks.