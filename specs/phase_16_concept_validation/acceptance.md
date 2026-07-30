# Phase 16 — Acceptance Criteria

## Functional acceptance

### FR-01: Concept/anatomy tensor extraction
- [ ] No-grad forward pass on source validation and target evaluation subjects
- [ ] Extracts all required tensors: concepts, c_target, g_bar, alpha, latent_logits, concept_logits, latent_probs, concept_probs
- [ ] Validates K matches atlas metadata
- [ ] Validates ROI-order hash matches concept-normalizer and atlas
- [ ] All values finite; alpha sums ≈ 1 per subject

### FR-02: Subject-level output contract
- [ ] Every evaluated subject exports all required fields
- [ ] Vector fields have exactly K entries in canonical ROI order
- [ ] Subject labels and artifacts consistent across folds/seeds

### FR-03: Fold and seed aggregation
- [ ] Source validation: true OOF, each source subject once per method/seed
- [ ] Target evaluation: fold-averaged concepts/probabilities/alpha; c_target/g_bar preserved
- [ ] Multiple seeds: fold-first then seed aggregation; per-seed records retained
- [ ] No repeated fold/seed predictions counted as independent subjects
- [ ] Directions not pooled

### FR-04: Concept fidelity metrics
- [ ] Global MAE, RMSE, mean signed bias
- [ ] Per-subject MAE/RMSE across ROIs
- [ ] Per-ROI MAE, RMSE, mean signed bias, Pearson, Spearman
- [ ] Correlations return availability status + reason when undefined
- [ ] Undefined correlations not replaced with zero

### FR-05: Anatomical consistency metrics
- [ ] Same structure as FR-04 (c_hat vs g_bar)
- [ ] Separate reporting: unweighted descriptive + canonical weighted
- [ ] No merged undocumented value
- [ ] No causal/pathological validity claims

### FR-06: Latent/concept-head agreement
- [ ] Latent-head predictive metrics
- [ ] Concept-head predictive metrics
- [ ] Top-1 agreement/disagreement rates
- [ ] Mean Jensen-Shannon divergence
- [ ] Canonical consistency direction from L_cons
- [ ] Per-class disagreement counts
- [ ] Predictive accuracy kept separate from concept fidelity

### FR-07: ROI-level stability
- [ ] Per-ROI fidelity/anatomy profiles, mean concept profiles, mean alpha profiles
- [ ] Pairwise Spearman rank correlation, mean pairwise, std across instances
- [ ] Top-k Jaccard overlap for configured k
- [ ] ROI rank dispersion
- [ ] Real-run top-k explicit in config; synthetic uses test-only values
- [ ] Terminology: attention profile, concept profile, ROI stability
- [ ] No causal importance, biomarker, disease mechanism terms

### FR-08: Class-conditional profiles
- [ ] Separate CN, MCI, AD profiles
- [ ] Mean predicted concept, c_target, g_bar per ROI
- [ ] Bootstrap CIs over subjects, class support
- [ ] No unrestricted ROI-by-ROI significance testing by default
- [ ] Inferential comparisons predeclared with multiplicity correction

### FR-09: Method comparisons
- [ ] Primary: prototype_pseudo vs {source_only, coral, mmd, cdan}
- [ ] Paired subjects
- [ ] Per-subject concept MAE, anatomy MAE, JS divergence
- [ ] Paired stratified bootstrap + Holm by direction/checkpoint/metric family
- [ ] No PADA vs AAGN/FasterSNN comparisons
- [ ] No target results for checkpoint/method selection

### FR-10: Figures and tables
- [ ] All 11 required machine-readable tables generated
- [ ] All 5 required figures generated
- [ ] Fixed ROI ordering
- [ ] No automatic cherry-picking of favorable ROIs
- [ ] Reduced top-k uses predeclared rule, retains complete table
- [ ] No causal intervention figures

### FR-11: Confidence intervals
- [ ] Reuses Phase 15 subject bootstrap
- [ ] Default: 95%, 10k replicates, subject unit, diagnosis stratification, explicit seed
- [ ] Tracks requested/successful/invalid replicates, unavailable metrics, seed
- [ ] No ROI bootstrapping; no fold bootstrapping before subject aggregation

### FR-12: Provenance and real-run gate
- [ ] Validates all 14 provenance fields
- [ ] Config contains explicit expected hashes + `authorized: false`
- [ ] Real run fails when unauthorized or hashes null
- [ ] Synthetic validation marked fixture-only
- [ ] Rejects incompatible concept-normalizer/ROI-order outputs

### FR-13: CLI
- [ ] Implements all required flags
- [ ] Dry-run: discovers, validates, reports missing, reports AAGN/FasterSNN N/A, no forward, no artifacts
- [ ] Validate-only: constructs dataset, loads checkpoint, one no-grad batch, validates dimensions/ROI order, no bootstrap/figures, no parameter update
- [ ] Never invokes training

## Non-functional acceptance

### NFR-01: Deterministic CPU execution
- [ ] Default runs on CPU
- [ ] CUDA tests optional

### NFR-02: Synthetic fixtures
- [ ] Small, deterministic
- [ ] No real ADNI/OASIS data required

### NFR-03: Tolerances
- [ ] No weakening only to pass
- [ ] Tolerances documented
- [ ] Exact equality where feasible
- [ ] Float32: explicit rtol/atol

### NFR-04: Resume consistency
- [ ] Interrupted/resumed matches uninterrupted when runtime contract supports it

## Regression acceptance

- [ ] Source-Only regression passes
- [ ] CORAL regression passes
- [ ] MMD regression passes
- [ ] CDAN regression passes
- [ ] prototype_pseudo regression passes
- [ ] AAGN regression passes
- [ ] FasterSNN regression passes
- [ ] Phase 15 predictive evaluation regression passes

## Exclusion acceptance

- [ ] AAGN reported as `not_applicable_no_pada3dacb_concept_head`
- [ ] FasterSNN reported as `not_applicable_no_pada3dacb_concept_head`
- [ ] Not treated as failed/incomplete
- [ ] No concept interventions
- [ ] No causal claims
- [ ] No ROI deletion/retraining
- [ ] No architecture ablations
- [ ] No manuscript rewriting
- [ ] No new training runs
- [ ] No real ADNI/OASIS evaluation
- [ ] No Phase 17 production code

## Manuscript score acceptance

For each of CFS, ACS, PCS, QIS:
- [ ] Exact equation recorded
- [ ] Source recorded
- [ ] Required inputs recorded
- [ ] Reduction/normalization recorded
- [ ] Loss vs posthoc distinguished
- [ ] BLOCKED if incomplete/ambiguous
- [ ] Not invented from name alone

## Validation commands

```bash
# Focused concept-evaluation tests
python -m pytest tests/test_concept_*.py -q --basetemp=artifacts/pytest-tmp-phase16

# Integration + regression
python -m pytest tests/test_concept_integration.py tests/test_concept_regressions.py -q --basetemp=artifacts/pytest-tmp-phase16

# Full suite
python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16

# Synthetic lifecycle
python scripts/evaluate_concepts.py --config configs/evaluation/concepts.yaml --runs-root runs --artifact-root artifacts --output-root results --dry-run --both-directions --all-pada-methods
python scripts/evaluate_concepts.py --config configs/evaluation/concepts.yaml --runs-root runs --artifact-root artifacts --output-root results --validate-only --direction ADNI_to_OASIS --all-pada-methods --bootstrap-seed 42
python scripts/evaluate_concepts.py --config configs/evaluation/concepts.yaml --runs-root runs --artifact-root artifacts --output-root results --direction ADNI_to_OASIS --all-pada-methods --checkpoint-policy best_source_f1 --bootstrap-replicates 100 --bootstrap-seed 42
python scripts/evaluate_concepts.py --config configs/evaluation/concepts.yaml --runs-root runs --artifact-root artifacts --output-root results --reuse --direction ADNI_to_OASIS --all-pada-methods --checkpoint-policy best_source_f1 --bootstrap-replicates 100 --bootstrap-seed 42

# Standard validation
python -m pip install -e .
python -c "import pada3dacb; print(pada3dacb.__version__)"
python -m ruff check .
git diff --check
```

All commands must exit 0 with expected results.