# Phase 16 — Manuscript Extraction

## Authoritative sources inspected

| Source | Status | Notes |
|--------|--------|-------|
| `notebooks/archive/training_original.ipynb` | ✅ Inspected | Contains PADA-3DACB training loop, concept/anatomy losses, forward pass definitions |
| `notebooks/archive/precompute_original.ipynb` | ✅ Inspected | Contains concept target extraction, normalizer fitting, artifact caching |
| `docs/PROPOSED_METHOD_EXPERIMENT.md` | ✅ Inspected | Describes proposed experimental methodology |
| Current manuscript/methodology in repo | ⚠️ Partial | No complete manuscript PDF found; extracted from docs and notebooks |

---

## Concept tensor definitions

### `concepts` (predicted concepts, c_hat)
- **Source**: PADA-3DACB forward pass → concept bottleneck → sigmoid-normalized output
- **Shape**: `[B, K]` where `K` = number of ROIs (atlas-dependent)
- **Range**: `[0, 1]` (sigmoid-normalized)
- **Semantics**: Predicted tissue-loss proxy per ROI, normalized by concept normalizer fitted on CN population
- **Notebook reference**: `training_original.ipynb` cell "Concept bottleneck forward", `precompute_original.ipynb` "Concept targets"

### `c_target` (concept targets)
- **Source**: Precomputed artifact per subject (`artifacts/concept_targets/<subject>_c_target.pt`)
- **Shape**: `[B, K]`
- **Range**: `[0, 1]` (same normalization as concepts)
- **Semantics**: Ground-truth tissue-loss proxy per ROI, derived from MRI intensity percentiles within atlas masks, normalized by CN-fitted concept normalizer
- **Notebook reference**: `precompute_original.ipynb` "Concept target precomputation"

### `g_bar` (anatomical targets)
- **Source**: Precomputed artifact per subject (`artifacts/anatomy/<subject>_g_bar.pt`)
- **Shape**: `[B, K]`
- **Range**: `[0, 1]` (normalized)
- **Semantics**: Canonical anatomical reference per ROI (e.g., expected atrophy pattern for diagnosis group), normalized by same concept normalizer
- **Notebook reference**: `precompute_original.ipynb` "Anatomical targets"

### `alpha` (attention weights)
- **Source**: PADA-3DACB forward pass → ROI attention module → softmax
- **Shape**: `[B, K]`
- **Range**: `[0, 1]`, sums to 1 per subject (`Σ_k alpha_k ≈ 1`)
- **Semantics**: Learned ROI gating weights reflecting model's attention distribution across ROIs for classification decision
- **Notebook reference**: `training_original.ipynb` "ROI attention module"

### `latent_logits`
- **Source**: PADA-3DACB forward pass → latent classifier head
- **Shape**: `[B, 3]` (CN, MCI, AD)
- **Semantics**: Raw logits for diagnosis classification from latent (global) features

### `concept_logits`
- **Source**: PADA-3DACB forward pass → concept-head classifier
- **Shape**: `[B, 3]` (CN, MCI, AD)
- **Semantics**: Raw logits for diagnosis classification from concept-bottleneck features

### `latent probabilities` (latent_probs)
- **Definition**: `softmax(latent_logits, dim=1)`
- **Shape**: `[B, 3]`
- **Semantics**: Latent-head diagnostic class probabilities

### `concept-head probabilities` (concept_probs)
- **Definition**: `softmax(concept_logits, dim=1)`
- **Shape**: `[B, 3]`
- **Semantics**: Concept-head diagnostic class probabilities

---

## Loss definitions

### `L_concept` (concept fidelity loss)
- **Equation**: `L_concept = MAE(c_hat, c_target)` or `MSE(c_hat, c_target)` per training config
- **Source**: `training_original.ipynb` "Loss computation" → `concept_loss = F.l1_loss(concepts, c_target)` (or MSE)
- **Role**: Training loss; supervises concept bottleneck to match c_target
- **Not a posthoc score**: Used in training, not evaluation

### `L_anat` (anatomical consistency loss)
- **Equation**: `L_anat = weighted_MAE(c_hat, g_bar)` with canonical ROI weights
- **Source**: `training_original.ipynb` "Loss computation" → `anat_loss = weighted_l1_loss(concepts, g_bar, weights=anat_weights)`
- **Role**: Training loss; encourages concepts to match canonical anatomical pattern
- **Not a posthoc score**: Used in training, not evaluation

### `L_cons` (consistency loss)
- **Equation**: `L_cons = KL(latent_probs || concept_probs)` or `JS(latent_probs, concept_probs)` per config
- **Source**: `training_original.ipynb` "Loss computation" → `cons_loss = F.kl_div(latent_log_probs, concept_probs)`
- **Role**: Training loss; enforces consistency between latent and concept heads
- **Direction**: `latent_probs` → `concept_probs` (latent supervises concept)
- **Not a posthoc score**: Used in training, not evaluation

---

## Manuscript scores search results

### CFS (Concept Fidelity Score)
- **Search**: `notebooks/archive/training_original.ipynb`, `notebooks/archive/precompute_original.ipynb`, `docs/PROPOSED_METHOD_EXPERIMENT.md`, `docs/PROPOSED_METHOD_EXPERIMENT.md`
- **Result**: **NO EXACT EQUATION FOUND**
- **Partial mentions**: "concept fidelity" mentioned descriptively; no formal definition
- **Status**: **BLOCKED** — Cannot implement without verified equation
- **Fallback**: Use transparent concept fidelity metrics (MAE, RMSE, bias, correlations per requirements)

### ACS (Anatomical Consistency Score)
- **Search**: Same sources
- **Result**: **NO EXACT EQUATION FOUND**
- **Partial mentions**: "anatomical consistency" mentioned; `L_anat` is a loss, not a posthoc score
- **Status**: **BLOCKED**
- **Fallback**: Use transparent anatomical consistency metrics (unweighted + canonical weighted per requirements)

### PCS (Predictive Consistency Score)
- **Search**: Same sources
- **Result**: **NO EXACT EQUATION FOUND**
- **Partial mentions**: `L_cons` is a training loss (KL/JS), not a posthoc evaluation score
- **Status**: **BLOCKED**
- **Fallback**: Use head agreement metrics (top-1 agreement, JS divergence, consistency direction per requirements)

### QIS (Quality/Interpretability Score)
- **Search**: Same sources
- **Result**: **NO EXACT EQUATION FOUND**
- **Status**: **BLOCKED**
- **Fallback**: Not implemented; transparent metrics cover descriptive evaluation

---

## Decision

All four manuscript-named scores (CFS, ACS, PCS, QIS) are **BLOCKED** due to missing verifiable equations in authoritative sources.

**Phase 16 will implement only the transparent metrics specified in requirements.md:**
- Concept fidelity: MAE, RMSE, bias, Pearson, Spearman (global, per-subject, per-ROI)
- Anatomical consistency: Same structure, unweighted + canonical weighted
- Head agreement: Predictive metrics, top-1 agreement, JS divergence, consistency direction, per-class disagreement
- ROI stability: Rank correlations, Jaccard, dispersion
- Class-conditional profiles: Descriptive means + bootstrap CIs

If complete manuscript equations become available in a later approved phase, they may be added as supplementary metrics without changing the core evaluation.