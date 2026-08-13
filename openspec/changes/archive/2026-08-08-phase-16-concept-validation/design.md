# Phase 16 — Design

## Architecture overview

Phase 16 adds a read-only concept-evaluation package under `src/pada3dacb/evaluation/concepts/` that consumes frozen PADA-3DACB checkpoints and precomputed concept/anatomy artifacts. No training modules are modified.

```
src/pada3dacb/evaluation/
├── __init__.py                    # Updated: exports concepts subpackage
├── schemas.py                     # Reused from Phase 15
├── bootstrap.py                   # Reused from Phase 15
├── paired_statistics.py           # Reused from Phase 15
├── multiple_testing.py            # Reused from Phase 15
├── tables.py                      # Reused from Phase 15
├── report.py                      # Reused from Phase 15
└── concepts/
    ├── __init__.py
    ├── schemas.py                 # Concept-specific schemas
    ├── dataset.py                 # Read-only concept-evaluation dataset
    ├── discovery.py               # Checkpoint/artifact discovery
    ├── provenance.py              # Provenance validation
    ├── inference.py               # No-grad subject inference
    ├── aggregation.py             # Fold/seed aggregation
    ├── fidelity.py                # Concept fidelity metrics
    ├── anatomy.py                 # Anatomical consistency metrics
    ├── agreement.py               # Head agreement metrics
    ├── stability.py               # ROI stability metrics
    ├── class_profiles.py          # Class-conditional profiles
    ├── statistics.py              # Bootstrap + paired stats + Holm
    ├── figures.py                 # Figure generation
    ├── tables.py                  # Table generation
    └── report.py                  # Report orchestration
```

## Data flow

### Input sources

1. **Checkpoints**: Frozen PADA-3DACB checkpoints from training runs (`runs/.../checkpoints/`)
2. **Artifacts**: Precomputed concept/anatomy artifacts (`artifacts/.../concept_targets/`, `artifacts/.../concept_normalizer.json`, `artifacts/.../atlas/`)
3. **Configuration**: `configs/evaluation/concepts.yaml`

### Processing pipeline

```
Discovery → Provenance Validation → Inference → Aggregation → Metrics → Figures/Tables → Report
```

1. **Discovery**: Scan `runs-root` for eligible PADA-3DACB checkpoints matching config selectors (direction, method, checkpoint-policy, seed, fold)
2. **Provenance**: Validate experiment hash, split hashes, atlas hash, ROI-order hash, concept-normalizer hash, model configuration hash
3. **Inference**: Load checkpoint in no-grad mode, run forward pass on subject batches, extract tensors
4. **Aggregation**: OOF for source; fold-ensemble for target; seed-level aggregation
5. **Metrics**: Fidelity, anatomy, agreement, stability, class profiles
6. **Statistics**: Subject bootstrap, paired comparisons, Holm correction
7. **Figures/Tables**: Generate machine-readable outputs
8. **Report**: Assemble manifests, write output tree

### Output structure

```
<output-root>/
└── concepts/
    └── <direction>/
        ├── primary_best_source_f1/
        │   ├── subject_outputs/
        │   ├── concept_fidelity/
        │   ├── anatomy_consistency/
        │   ├── head_agreement/
        │   ├── roi_stability/
        │   ├── class_profiles/
        │   ├── paired_comparisons/
        │   ├── figures/
        │   └── tables/
        └── sensitivity_last/
            └── ...
```

Root artifacts:
- `evaluation_manifest.json`
- `evaluation_config_resolved.yaml`
- `provenance_report.json`
- `method_status.csv`
- `evaluation_log.txt`

Every artifact references: evaluation config hash, input checkpoint hashes, artifact hashes, ROI-order hash, concept-normalizer hash, aggregation policy, checkpoint policy, statistical protocol version.

## Tensor contracts

### Input tensors (from checkpoint forward pass)

| Tensor | Shape | Description |
|--------|-------|-------------|
| `concepts` | `[B, K]` | Predicted concept values (normalized) |
| `c_target` | `[B, K]` | Concept targets (from artifacts) |
| `g_bar` | `[B, K]` | Anatomical targets (from artifacts) |
| `alpha` | `[B, K]` | Attention weights (softmax over ROIs) |
| `latent_logits` | `[B, 3]` | Latent classification logits |
| `concept_logits` | `[B, 3]` | Concept-head classification logits |
| `latent_probs` | `[B, 3]` | `softmax(latent_logits, dim=1)` |
| `concept_probs` | `[B, 3]` | `softmax(concept_logits, dim=1)` |

### Derived tensors

| Tensor | Shape | Description |
|--------|-------|-------------|
| `latent_prediction` | `[B]` | `argmax(latent_probs, dim=1)` |
| `concept_prediction` | `[B]` | `argmax(concept_probs, dim=1)` |
| `predicted_concepts` | `[B, K]` | Same as concepts (for clarity) |
| `concept_targets` | `[B, K]` | Same as c_target |
| `anatomical_targets` | `[B, K]` | Same as g_bar |
| `attention_alpha` | `[B, K]` | Same as alpha |

### Validation rules

- `K` matches atlas metadata (number of ROIs)
- ROI-order hash matches concept-normalizer and atlas
- All values finite
- `concepts`, `c_target`, `g_bar` in expected ranges (normalized [0,1] for concepts)
- `alpha` sums approximately to 1 per subject (softmax)
- Subject labels and artifacts consistent across folds/seeds

### Output format

Vector fields stored as columns in CSV/Parquet with ROI-indexed columns (`roi_0`, `roi_1`, ..., `roi_{K-1}`) plus metadata columns.

## Metric equations

### Concept fidelity (c_hat vs c_target)

**Global MAE**: `MAE = (1/(N*K)) * Σ_i Σ_k |c_hat_ik - c_target_ik|`

**Global RMSE**: `RMSE = sqrt((1/(N*K)) * Σ_i Σ_k (c_hat_ik - c_target_ik)^2)`

**Global mean signed bias**: `Bias = (1/(N*K)) * Σ_i Σ_k (c_hat_ik - c_target_ik)`

**Per-subject MAE**: `MAE_i = (1/K) * Σ_k |c_hat_ik - c_target_ik|`

**Per-subject RMSE**: `RMSE_i = sqrt((1/K) * Σ_k (c_hat_ik - c_target_ik)^2)`

**Per-ROI MAE**: `MAE_k = (1/N) * Σ_i |c_hat_ik - c_target_ik|`

**Per-ROI RMSE**: `RMSE_k = sqrt((1/N) * Σ_i (c_hat_ik - c_target_ik)^2)`

**Per-ROI mean signed bias**: `Bias_k = (1/N) * Σ_i (c_hat_ik - c_target_ik)`

**Per-ROI Pearson correlation**: `r_k = corr(c_hat_{:,k}, c_target_{:,k})` with availability status

**Per-ROI Spearman correlation**: `ρ_k = spearman(c_hat_{:,k}, c_target_{:,k})` with availability status

**Correlation availability**:
- If ROI is constant (std ≈ 0): `UNAVAILABLE`, reason `constant_roi`
- If N < 3: `UNAVAILABLE`, reason `insufficient_samples`
- If numerical evaluation fails: `UNAVAILABLE`, reason `numerical_error`
- Do not replace undefined with zero

### Anatomical consistency (c_hat vs g_bar)

Same equations as concept fidelity, applied to `c_hat_ik` vs `g_bar_ik`.

**Unweighted descriptive anatomy agreement**: Global/per-subject/per-ROI MAE/RMSE/bias/Pearson/Spearman as above.

**Canonical weighted anatomy score**: `Weighted_Score = Σ_k w_k * MAE_k` where `w_k` are canonical ROI weights from anatomical loss (if available). Report separately from unweighted metrics.

### Head agreement

**Latent-head predictive metrics**: Accuracy, balanced accuracy, macro-F1, per-class F1 from `latent_prediction` vs `true_label`

**Concept-head predictive metrics**: Same from `concept_prediction` vs `true_label`

**Top-1 agreement rate**: `(1/N) * Σ_i I(latent_prediction_i == concept_prediction_i)`

**Top-1 disagreement rate**: `1 - agreement_rate`

**Mean Jensen-Shannon divergence**: `JS(p_latent, p_concept) = (1/2) * KL(p_latent || m) + (1/2) * KL(p_concept || m)` where `m = (p_latent + p_concept) / 2`, averaged over subjects

**Canonical consistency-loss direction**: Derived from `L_cons = KL(latent_probs || concept_probs)` — direction of consistency pressure

**Per-class disagreement counts**: Confusion matrix between `latent_prediction` and `concept_prediction` per true class

### ROI stability

**Pairwise Spearman rank correlation**: For each pair of model instances (fold/seed combinations), compute Spearman correlation between ROI profiles (concept fidelity, anatomy consistency, mean concepts, mean alpha)

**Mean pairwise rank correlation**: Average of pairwise correlations

**Standard deviation across model instances**: Per-ROI std of metric values across instances

**Top-k Jaccard overlap**: For configured k, Jaccard overlap of top-k ROI sets between instances

**ROI rank dispersion**: Std of ROI ranks across instances

### Class-conditional profiles

Per class `c ∈ {CN, MCI, AD}`:
- Mean predicted concept per ROI: `(1/N_c) Σ_{i:y_i=c} c_hat_ik`
- Mean c_target per ROI: `(1/N_c) Σ_{i:y_i=c} c_target_ik`
- Mean g_bar per ROI: `(1/N_c) Σ_{i:y_i=c} g_bar_ik`
- Bootstrap CI over subjects (Phase 15 infrastructure)
- Class support: `N_c`

### Method comparisons

**Paired subject bootstrap**: For each bootstrap replicate, sample subjects with replacement within each class (stratified), compute metric difference between paired methods

**Holm correction**: By direction, checkpoint policy, metric family (concept MAE, anatomy MAE, JS divergence)

## Configuration

### `configs/evaluation/concepts.yaml`

```yaml
schema_version: "1.0"
protocol_version: "1.0"
class_order:
  CN: 0
  MCI: 1
  AD: 2
methods:
  - source_only
  - coral
  - mmd
  - cdan
  - prototype_pseudo
  - aagn
  - faster_snn
directions:
  - adni_to_oasis
  - oasis_to_adni
expected_folds: [0, 1, 2, 3, 4]
expected_seeds: [42]
checkpoint_policies:
  primary: best_source_f1
  sensitivity: last
bootstrap:
  replicates: 10000
  seed: 12345
  ci_policy: percentile_95_linear
  stratification: diagnosis_class
top_k:
  - 5
  - 10
  - 20
real_evaluation_gate:
  authorized: false
  authorized_exports: null
  D-14-001: null
  D-14-002: null
  protocol_approval: null
concept_normalizer:
  expected_hash: null
atlas:
  expected_roi_order_hash: null
  expected_atlas_hash: null
```

### Device selection

`--device` CLI argument: `cpu` (default) or `cuda` (optional). Inference runs on specified device.

## Provenance validation

Each candidate must prove:
- Method, direction, cohorts, seed, fold, logical checkpoint, checkpoint epoch
- Experiment/model/training hashes (exact-byte SHA-256)
- Split and partition hashes
- Atlas/ROI ordering hash (when applicable)
- Fixed class order `(CN,MCI,AD)=(0,1,2)`
- Concept-normalizer hash
- Artifact assignment

Missing or conflicting provenance → exclude affected candidate.

Source-Only must prove target-evaluation membership.

## Checkpoint compatibility

Read-only checkpoint loading:
- No optimizer/scheduler state required
- No training hyperparameters required
- Only model weights and architecture config
- Compatibility validated by hash comparison

## Reuse of Phase 15 utilities

- `bootstrap.py`: Subject-level stratified bootstrap (PCG64, no redraw)
- `paired_statistics.py`: Exact McNemar, paired bootstrap differences
- `multiple_testing.py`: Six-slot Holm correction
- `tables.py`: CSV/Parquet table generation utilities
- `report.py`: Manifest, atomic write, reuse verification
- `schemas.py`: Reused enums (Direction, CheckpointPolicy, MethodId)

## Error handling

- No training imports or invocation
- No gradient computation
- No concept normalizer refitting
- No concept/Jacobian recomputation
- No subject assignment changes
- All validation failures exclude candidate, do not crash pipeline
- Real gate failure enumerates all unresolved gates before statistics

## Testing strategy

- Deterministic CPU fixtures
- Synthetic checkpoints with known tensor values
- Fixed ROI order (K=5 for tests)
- Synthetic concept-normalizer with known mu/sigma
- Phase 15 regression tests for all prior behavior
- No real MRI data required

## Planning mirror and ownership boundary

The planning artifacts mirror one approved contract: proposal, capability specification, this design, tasks, and `specs/phase_16_concept_validation/agent_plan.yaml`.

- WU-13 is limited to those mirrors and may not alter evaluation implementation, tests, training/adaptation code, real-data inputs, or Phase 17 paths.
- Every task row has exactly one terminal owner marker. Implementation rows cover synthetic/specification work; parent rows cover bounded review and native delivery lifecycle actions.
- Work units are serially bounded by start, finish, verification, and rollback evidence. The current delivery plan is `auto-chain` / `feature-branch-chain`, with a hard 400-authored-line ceiling and no size exception.
- Native receipt #1793 remains an administrative delivery blocker for branches, commits, PRs, archive, release, and publication. It does not block mirror maintenance or synthetic implementation/verification.
- The plan reports AAGN/FasterSNN as not applicable, keeps CFS/ACS/PCS/QIS blocked without authoritative equations, preserves `authorized: false`, and forbids training/adaptation changes and Phase 17 production work.