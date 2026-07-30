# Phase 16 — Metric Protocol

## Overview

This document specifies the exact equations, aggregation rules, and unavailable handling for all Phase 16 metrics. All metrics are descriptive/evaluative only — no training losses, no causal claims.

## Notation

- `B`: batch size (subjects)
- `K`: number of ROIs (atlas-dependent)
- `N_s`: number of subjects
- `N_f`: number of folds
- `N_d`: number of seeds
- `c_hat[b, k]`: predicted concept for subject b, ROI k
- `c_target[b, k]`: concept target for subject b, ROI k
- `g_bar[b, k]`: anatomical target for subject b, ROI k
- `alpha[b, k]`: attention weight for subject b, ROI k
- `latent_probs[b, c]`: latent-head probability for class c
- `concept_probs[b, c]`: concept-head probability for class c
- `latent_pred[b]`: `argmax_c latent_probs[b, c]`
- `concept_pred[b]`: `argmax_c concept_probs[b, c]`
- `y_true[b]`: true diagnosis label (0=CN, 1=MCI, 2=AD)

---

## 1. Concept Fidelity Metrics (c_hat vs c_target)

### 1.1 Global metrics (over all subjects and ROIs)

```python
# Flatten all (subject, ROI) pairs
flat_hat = c_hat.flatten()        # shape (N_s * K,)
flat_target = c_target.flatten()  # shape (N_s * K,)

MAE_global   = mean(|flat_hat - flat_target|)
RMSE_global  = sqrt(mean((flat_hat - flat_target)^2))
Bias_global  = mean(flat_hat - flat_target)  # signed
```

### 1.2 Per-subject metrics (across ROIs)

```python
# For each subject b
MAE_subj[b]  = mean_k(|c_hat[b, k] - c_target[b, k]|)
RMSE_subj[b] = sqrt(mean_k((c_hat[b, k] - c_target[b, k])^2))
```

### 1.3 Per-ROI metrics (across subjects)

```python
# For each ROI k
MAE_roi[k]   = mean_b(|c_hat[b, k] - c_target[b, k]|)
RMSE_roi[k]  = sqrt(mean_b((c_hat[b, k] - c_target[b, k])^2))
Bias_roi[k]  = mean_b(c_hat[b, k] - c_target[b, k])  # signed
```

### 1.4 Per-ROI correlations

```python
# For each ROI k
x = c_hat[:, k]      # shape (N_s,)
y = c_target[:, k]   # shape (N_s,)

if len(unique(x)) <= 1 or len(unique(y)) <= 1 or N_s < 3:
    status = UNAVAILABLE
    reason = "constant_roi" or "insufficient_samples"
    pearson = spearman = None
else:
    pearson = pearsonr(x, y)
    spearman = spearmanr(x, y)
    status = AVAILABLE
    reason = None
```

**Unavailable reasons**: `constant_roi`, `insufficient_samples`, `numerical_error`

---

## 2. Anatomical Consistency Metrics (c_hat vs g_bar)

Identical structure to Section 1, replacing `c_target` with `g_bar`.

### 2.1 Global
```python
MAE_global   = mean(|c_hat - g_bar|)
RMSE_global  = sqrt(mean((c_hat - g_bar)^2))
Bias_global  = mean(c_hat - g_bar)
```

### 2.2 Per-subject, per-ROI
Same formulas as 1.2, 1.3 with `g_bar`.

### 2.3 Per-ROI correlations
Same as 1.4 with `g_bar`.

### 2.4 Canonical weighted anatomy score

```python
# anat_weights[k] from canonical anatomical loss weights (sum = 1)
# If weights unavailable, score = UNAVAILABLE, reason="weights_unavailable"

weighted_MAE   = sum_k(anat_weights[k] * MAE_roi[k])
weighted_RMSE  = sqrt(sum_k(anat_weights[k] * RMSE_roi[k]^2))
weighted_Bias  = sum_k(anat_weights[k] * Bias_roi[k])
```

**Report separately**: unweighted descriptive (Sections 2.1-2.3) and canonical weighted (2.4). Do not merge.

---

## 3. Head Agreement Metrics

### 3.1 Latent-head predictive metrics
Use Phase 15 `compute_metrics` on `latent_probs` with true labels `y_true`.
Outputs: accuracy, balanced_accuracy, macro_f1, per-class precision/recall/f1, macro_AUC, macro_AP, etc.

### 3.2 Concept-head predictive metrics
Same as 3.1 on `concept_probs`.

### 3.3 Top-1 agreement
```python
agreement_rate = mean(latent_pred == concept_pred)
disagreement_rate = 1 - agreement_rate
```

### 3.4 Per-class disagreement counts
```python
# For each true class c in {0,1,2}
disagree_count[c] = sum((latent_pred != concept_pred) & (y_true == c))
total_count[c] = sum(y_true == c)
disagree_rate[c] = disagree_count[c] / total_count[c] if total_count[c] > 0 else UNAVAILABLE
```

### 3.5 Mean Jensen-Shannon divergence
```python
# For each subject b
def js_divergence(p, q):
    m = 0.5 * (p + q)
    return 0.5 * (kl_div(p, m) + kl_div(q, m))

js_b = js_divergence(latent_probs[b], concept_probs[b])
mean_js = mean_b(js_b)
```

### 3.6 Canonical consistency direction
From `L_cons` definition (KL or JS):
- If `L_cons = KL(latent || concept)`: latent → concept (latent supervises concept)
- If `L_cons = JS(latent, concept)`: symmetric
- Report direction explicitly: `latent_supervises_concept` or `symmetric`

---

## 4. ROI-Level Stability Metrics

### 4.1 Input profiles
For each model instance (method × seed × fold):
- `fidelity_profile[i, k]`: per-ROI concept fidelity (e.g., MAE_roi[k])
- `anatomy_profile[i, k]`: per-ROI anatomy consistency (e.g., MAE_roi[k])
- `concept_profile[i, k]`: mean predicted concept across subjects
- `alpha_profile[i, k]`: mean attention alpha across subjects

### 4.2 Pairwise Spearman rank correlation
```python
# For each pair of instances (i, j)
rho_fidelity[i, j] = spearmanr(fidelity_profile[i], fidelity_profile[j])
rho_anatomy[i, j]  = spearmanr(anatomy_profile[i], anatomy_profile[j])
rho_concept[i, j]  = spearmanr(concept_profile[i], concept_profile[j])
rho_alpha[i, j]    = spearmanr(alpha_profile[i], alpha_profile[j])
```

### 4.3 Mean pairwise rank correlation
```python
mean_rho_fidelity = mean(rho_fidelity[i, j] for all i < j)
# Similarly for anatomy, concept, alpha
```

### 4.3 Standard deviation across instances
```python
std_fidelity[k] = std(fidelity_profile[:, k])  # per ROI
# Similarly for anatomy, concept, alpha
```

### 4.4 Top-k Jaccard overlap
```python
# For each instance i, get top-k ROIs by concept_profile
top_k_indices[i] = argsort(concept_profile[i])[-k:]

# Pairwise Jaccard
jaccard[i, j] = |top_k_indices[i] ∩ top_k_indices[j]| / |top_k_indices[i] ∪ top_k_indices[j]|
mean_jaccard = mean(jaccard[i, j] for all i < j)
```

**Configured k values**: explicit in `concepts.yaml` (e.g., `[5, 10, 20]`). Synthetic fixtures use small values.

### 4.5 ROI rank dispersion
```python
# Rank each instance's concept profile
rank[i, k] = rank of concept_profile[i, k] (1 = highest)

# Dispersion per ROI
rank_std[k] = std(rank[:, k])
rank_range[k] = max(rank[:, k]) - min(rank[:, k])
```

---

## 5. Class-Conditional Descriptive Profiles

For each class `c in {CN=0, MCI=1, AD=2}`:
```python
mask = (y_true == c)
support[c] = sum(mask)

mean_concept[c, k] = mean(c_hat[mask, k])
mean_c_target[c, k] = mean(c_target[mask, k])
mean_g_bar[c, k] = mean(g_bar[mask, k])

# Bootstrap CIs over subjects (reuse Phase 15 infrastructure)
ci_concept[c, k] = bootstrap_ci(mean_concept[c, k], replicates=10000, seed=explicit)
```

---

## 6. Method Comparisons

### 6.1 Primary comparisons
`prototype_pseudo` vs each of `{source_only, coral, mmd, cdan}`

### 6.2 Comparison metrics (per subject)
```python
# For each method m and paired subject b in target evaluation
concept_error_m_b = MAE(c_hat_m[b], c_target[b])
anatomy_error_m_b = MAE(c_hat_m[b], g_bar[b])
head_js_m_b = JS(latent_probs_m[b], concept_probs_m[b])

# Paired differences use the fixed orientation prototype_pseudo - comparator
concept_MAE_diff_b = concept_error_prototype_pseudo_b - concept_error_comparator_b
anatomy_MAE_diff_b = anatomy_error_prototype_pseudo_b - anatomy_error_comparator_b
js_div_diff_b = head_js_prototype_pseudo_b - head_js_comparator_b
```

### 6.3 Paired bootstrap + Holm
- Stratified subject bootstrap (Phase 15)
- Four-comparator Holm family within each `(direction, checkpoint_policy, metric_family)` stratum
- Comparators are exactly `{source_only, coral, mmd, cdan}`; AAGN and FasterSNN are not applicable
- Metric families: `concept_MAE`, `anatomy_MAE`, `js_divergence`

---

## 7. Bootstrap Protocol (reuse Phase 15)

- Resampling unit: **subject** (not ROI, not fold)
- Stratification: diagnosis class (CN, MCI, AD)
- Default: 10,000 replicates, explicit seed, 95% CI, percentile method
- Track: requested, successful, invalid, unavailable
- **Never** bootstrap ROI entries as independent subjects
- **Never** bootstrap fold outputs before subject aggregation

---

## 8. Unavailable Handling

| Condition | Metric | Status | Reason |
|-----------|--------|--------|--------|
| Constant ROI | Pearson/Spearman | UNAVAILABLE | constant_roi |
| N < 3 | Pearson/Spearman | UNAVAILABLE | insufficient_samples |
| Numerical error | Any correlation | UNAVAILABLE | numerical_error |
| Weights missing | Canonical weighted anatomy | UNAVAILABLE | weights_unavailable |
| Class support = 0 | Per-class disagreement | UNAVAILABLE | zero_support |
| Empty group | Any per-class/group | UNAVAILABLE | empty_group |

**Never** replace unavailable with zero. Report explicitly.

---

## 9. Verification

Each metric function has a reference test against:
- Direct NumPy/SciPy computation
- Known analytic result (e.g., MAE of identical arrays = 0)
- Edge cases (constant, NaN, empty)

Reference tests in `tests/test_concept_metrics_reference.py`.