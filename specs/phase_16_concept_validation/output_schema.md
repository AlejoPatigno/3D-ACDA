# Phase 16 — Output Schema

## Root artifacts

At the concept-evaluation output root:

```
<output-root>/
├── evaluation_manifest.json
├── evaluation_config_resolved.yaml
├── provenance_report.json
├── method_status.csv
├── evaluation_log.txt
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

### `evaluation_manifest.json`

```json
{
  "schema_version": "1.0",
  "protocol_version": "1.0",
  "evaluation_identity": "<sha256>",
  "analysis_mode": "synthetic",
  "created_utc": "2026-07-28T12:00:00Z",
  "completed_utc": "2026-07-28T12:05:00Z",
  "methods": ["source_only", "coral", "mmd", "cdan", "prototype_pseudo"],
  "directions": ["adni_to_oasis", "oasis_to_adni"],
  "checkpoint_policies": ["best_source_f1", "last"],
  "class_order": {"CN": 0, "MCI": 1, "AD": 2},
  "bootstrap": {
    "replicates": 10000,
    "seed": 12345,
    "ci_policy": "percentile_95_linear"
  },
  "configuration_sha256": "<config_sha256>",
  "authorization_sha256": "<auth_sha256>",
  "gate_states": {
    "authorized_exports": false,
    "concept_normalizer": false,
    "atlas_hash": false,
    "protocol_approval": false
  },
  "ordered_input_sha256s": ["<sha1>", "<sha2>", ...],
  "identity_inputs": {...},
  "library_versions": {"numpy": "...", "scipy": "...", "scikit-learn": "...", "torch": "..."},
  "output_sha256s": {
    "concepts/adni_to_oasis/primary_best_source_f1/tables/concept_fidelity_global.csv": "<sha256>",
    ...
  },
  "disposition": "completed"
}
```

### `evaluation_config_resolved.yaml`
Complete resolved configuration (all defaults filled, hashes validated).

### `provenance_report.json`
```json
{
  "candidates": [
    {
      "method_id": "source_only",
      "direction": "adni_to_oasis",
      "checkpoint_policy": "best_source_f1",
      "seed": 42,
      "fold": 0,
      "status": "included",
      "experiment_hash": "...",
      "model_hash": "...",
      "training_hash": "...",
      "split_hashes": {...},
      "atlas_hash": "...",
      "roi_order_hash": "...",
      "concept_normalizer_hash": "...",
      "artifact_assignment": {...}
    },
    ...
  ],
  "excluded": [
    {
      "method_id": "aagn",
      "reason": "not_applicable_no_pada3dacb_concept_head"
    },
    ...
  ],
  "validation_issues": [...]
}
```

### `method_status.csv`
| method_id | direction | checkpoint_policy | expected_folds | completed_folds | expected_seeds | completed_seeds | status | reason_code | reason_detail |
|---|---|---|---|---|---|---|---|---|---|
| source_only | adni_to_oasis | best_source_f1 | 0,1,2,3,4 | 0,1,2,3,4 | 42 | 42 | included | - | - |
| aagn | adni_to_oasis | best_source_f1 | - | - | - | - | not_applicable_no_pada3dacb_concept_head | - | - |

---

## Direction-level structure

```
concepts/<direction>/<checkpoint_policy>/
├── subject_outputs/
│   ├── <method>_fold0_seed42.csv
│   ├── <method>_fold1_seed42.csv
│   └── ...
├── concept_fidelity/
│   ├── global.csv
│   ├── per_subject.csv
│   ├── per_roi.csv
│   └── correlations.csv
├── anatomy_consistency/
│   ├── global.csv
│   ├── per_subject.csv
│   ├── per_roi.csv
│   ├── correlations.csv
│   └── weighted_score.csv
├── head_agreement/
│   ├── latent_predictive.csv
│   ├── concept_predictive.csv
│   ├── top1_agreement.csv
│   ├── js_divergence.csv
│   ├── consistency_direction.csv
│   └── per_class_disagreement.csv
├── roi_stability/
│   ├── rank_correlations.csv
│   ├── mean_pairwise_rho.csv
│   ├── instance_std.csv
│   ├── jaccard_overlap.csv
│   └── rank_dispersion.csv
├── class_profiles/
│   ├── cn_concepts.csv
│   ├── mci_concepts.csv
│   ├── ad_concepts.csv
│   ├── cn_c_targets.csv
│   ├── ...
│   ├── cn_g_bar.csv
│   └── ...
├── paired_comparisons/
│   ├── concept_mae_paired.csv
│   ├── anatomy_mae_paired.csv
│   ├── js_divergence_paired.csv
│   └── holm_adjusted.csv
├── figures/
│   ├── concept_fidelity_roi_heatmap.png
│   ├── anatomy_consistency_roi_heatmap.png
│   ├── head_agreement_matrix.png
│   ├── roi_stability_heatmap.png
│   └── class_conditional_concept_profiles.png
└── tables/
    ├── concept_fidelity_global.csv
    ├── concept_fidelity_per_subject.csv
    ├── concept_fidelity_per_roi.csv
    ├── anatomy_consistency_global.csv
    ├── anatomy_consistency_per_subject.csv
    ├── anatomy_consistency_per_roi.csv
    ├── head_agreement.csv
    ├── roi_stability.csv
    ├── class_conditional_profiles.csv
    ├── paired_method_comparisons.csv
    └── method_status.csv
```

---

## Subject outputs

### `<method>_fold<F>_seed<S>.csv` (or aggregated `subject_outputs/<method>.csv`)

| Column | Type | Description |
|--------|------|-------------|
| method | str | Method ID |
| model | str | Model name |
| direction | str | adni_to_oasis / oasis_to_adni |
| source_domain | str | ADNI / OASIS |
| target_domain | str | OASIS / ADNI |
| seed | int | Seed |
| fold | int | Fold |
| logical_checkpoint | str | best_source_f1 / last |
| checkpoint_epoch | int | Epoch number |
| experiment_hash | str | SHA-256 |
| subject_id | str | Original subject ID |
| subject_hash | str | SHA-256 (stable, approved) |
| cohort | str | ADNI / OASIS |
| true_label | int | 0/1/2 |
| label_name | str | CN / MCI / AD |
| predicted_concepts_roi_0 ... roi_K-1 | float32 | Predicted concepts per ROI |
| concept_targets_roi_0 ... roi_K-1 | float32 | Concept targets per ROI |
| anatomical_targets_roi_0 ... roi_K-1 | float32 | g_bar per ROI |
| attention_alpha_roi_0 ... roi_K-1 | float32 | Attention weights per ROI |
| latent_probabilities_CN | float32 | Latent head CN prob |
| latent_probabilities_MCI | float32 | Latent head MCI prob |
| latent_probabilities_AD | float32 | Latent head AD prob |
| concept_probabilities_CN | float32 | Concept head CN prob |
| concept_probabilities_MCI | float32 | Concept head MCI prob |
| concept_probabilities_AD | float32 | Concept head AD prob |
| latent_prediction | int | 0/1/2 |
| concept_prediction | int | 0/1/2 |

Vector columns use fixed ROI order: `roi_0` through `roi_{K-1}`.

---

## Concept fidelity tables

### `concept_fidelity_global.csv`
| metric | value | status | reason |
|---|---|---|---|
| MAE_global | 0.123 | AVAILABLE | - |
| RMSE_global | 0.145 | AVAILABLE | - |
| Bias_global | -0.012 | AVAILABLE | - |

### `concept_fidelity_per_subject.csv`
| subject_hash | MAE | RMSE | status | reason |
|---|---|---|---|---|
| <sha> | 0.11 | 0.13 | AVAILABLE | - |

### `concept_fidelity_per_roi.csv`
| roi_index | MAE | RMSE | Bias | Pearson | Pearson_status | Pearson_reason | Spearman | Spearman_status | Spearman_reason |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.10 | 0.12 | -0.01 | 0.85 | AVAILABLE | - | 0.82 | AVAILABLE | - |

### `correlations.csv` (separate for fidelity/anatomy)
| roi_index | pearson | pearson_status | pearson_reason | spearman | spearman_status | spearman_reason |
|---|---|---|---|---|---|---|
| 0 | 0.85 | AVAILABLE | - | 0.82 | AVAILABLE | - |

---

## Anatomical consistency tables

### `anatomy_consistency_global.csv`
| metric | value | status | reason |
|---|---|---|---|
| MAE_global | 0.098 | AVAILABLE | - |

### `anatomy_consistency_per_roi.csv`
Same structure as concept_fidelity_per_roi.

### `weighted_score.csv`
| metric | value | status | reason |
|---|---|---|---|
| weighted_MAE | 0.087 | AVAILABLE | - |
| weighted_RMSE | 0.112 | AVAILABLE | - |
| weighted_Bias | -0.005 | AVAILABLE | - |

---

## Head agreement tables

### `latent_predictive.csv` / `concept_predictive.csv`
| metric | value | status | reason |
|---|---|---|---|
| accuracy | 0.82 | AVAILABLE | - |
| balanced_accuracy | 0.78 | AVAILABLE | - |
| macro_f1 | 0.75 | AVAILABLE | - |

### `top1_agreement.csv`
| metric | value |
|---|---|
| agreement_rate | 0.71 |
| disagreement_rate | 0.29 |

### `js_divergence.csv`
| metric | value |
|---|---|
| mean_js_divergence | 0.034 |

### `consistency_direction.csv`
| direction |
|---|
| latent_supervises_concept |

### `per_class_disagreement.csv`
| true_class | disagree_count | total_count | disagree_rate | status | reason |
|---|---|---|---|---|---|
| 0 (CN) | 12 | 45 | 0.267 | AVAILABLE | - |

---

## ROI stability tables

### `rank_correlations.csv`
| instance_i | instance_j | rho_fidelity | rho_anatomy | rho_concept | rho_alpha |
|---|---|---|---|---|---|
| pseudo_fold0_seed42 | pseudo_fold1_seed42 | 0.87 | 0.82 | 0.84 | 0.79 |

### `mean_pairwise_rho.csv`
| profile | mean_rho |
|---|---|
| fidelity | 0.85 |
| anatomy | 0.81 |
| concept | 0.83 |
| alpha | 0.78 |

### `instance_std.csv`
| roi_index | std_fidelity | std_anatomy | std_concept | std_alpha |
|---|---|---|---|---|
| 0 | 0.02 | 0.01 | 0.03 | 0.04 |

### `jaccard_overlap.csv`
| k | mean_jaccard |
|---|---|
| 5 | 0.68 |
| 10 | 0.72 |
| 20 | 0.75 |

### `rank_dispersion.csv`
| roi_index | rank_std | rank_range |
|---|---|---|
| 0 | 1.2 | 4 |

---

## Class conditional profiles

### `cn_concepts.csv` (and MCI, AD)
| roi_index | mean_predicted_concept | ci_lower | ci_upper | mean_c_target | mean_g_bar | support |
|---|---|---|---|---|---|---|
| 0 | 0.15 | 0.12 | 0.18 | 0.14 | 0.16 | 45 |

### `cn_c_targets.csv`, `cn_g_bar.csv`
Same structure.

---

## Paired method comparisons

### `concept_mae_paired.csv`
| method_a | method_b | direction | checkpoint_policy | subject_hash | diff |
|---|---|---|---|---|---|
| prototype_pseudo | source_only | adni_to_oasis | best_source_f1 | <sha> | -0.02 |

### `anatomy_mae_paired.csv`
Same structure.

### `js_divergence_paired.csv`
| method_a | method_b | direction | checkpoint_policy | subject_hash | js_diff |
|---|---|---|---|---|---|
| prototype_pseudo | source_only | adni_to_oasis | best_source_f1 | <sha> | -0.005 |

### `holm_adjusted.csv`
| family | metric | comparator | raw_p | adj_p | significant |
|---|---|---|---|---|---|
| concept_mae:adni_to_oasis:best_source_f1 | concept_mae | source_only | 0.032 | 0.192 | False |

---

## Figures

| File | Description |
|---|---|
| `concept_fidelity_roi_heatmap.png` | K×N heatmap of per-ROI MAE (methods × ROIs) |
| `anatomy_consistency_roi_heatmap.png` | K×N heatmap of per-ROI anatomy MAE |
| `head_agreement_matrix.png` | Confusion matrix: latent vs concept predictions |
| `roi_stability_heatmap.png` | Rank correlation heatmap across instances |
| `class_conditional_concept_profiles.png` | Line plot: mean concept per ROI per class |

All figures use fixed ROI ordering. No automatic cherry-picking. Top-k figures use predeclared rule, complete table retained.

---

## Validation rules

Every artifact must include:
- `evaluation_configuration_hash`
- `input_checkpoint_hashes` (list)
- `artifact_hashes` (list)
- `roi_order_hash`
- `concept_normalizer_hash`
- `aggregation_policy` (e.g., "fold_then_seed")
- `checkpoint_policy` (best_source_f1 / last)
- `statistical_protocol_version` (e.g., "phase15_bootstrap_v1")

Reuse verification checks exact match of identity inputs, library versions, output hashes.