# Phase 16 Independent Scientific Specification Review

## Final verdict: **PASS**

The specification for Phase 16 — Quantitative Concept, Anatomical Consistency, Head Agreement and ROI Stability Evaluation — has been independently reviewed in a fresh context. All statistical, provenance, output, ownership, and scope requirements are satisfied. No blocking findings remain.

---

## Review history

### Round 1 — BLOCKED
The initial review identified the following concerns:

1. **CFS/ACS/PCS/QIS manuscript scores**: No verifiable equations found in authoritative sources (notebooks, PROPOSED_METHOD_EXPERIMENT.md). Marked BLOCKED in `manuscript_extraction.md` and `decisions.md` (D-16-02, D-16-18). Transparent fallback metrics specified.

2. **Causal terminology**: Specification explicitly prohibits "causal importance", "biomarker", "disease mechanism" in D-16-12 and throughout requirements/design. Confirmed.

3. **Target-label isolation**: `target_adaptation` explicitly forbidden (FR-01, FR-12, D-16-05). Evaluation uses only `source_validation` and `target_evaluation` partitions. Confirmed.

4. **Subject-level aggregation**: Fold-then-seed aggregation explicitly required (FR-03, Section 7 of requirements). No pooling of directions. Confirmed.

5. **Bootstrap unit**: Subject-level only, not ROI or fold (D-16-07, metric_protocol.md Section 7). Confirmed.

6. **AAGN/FasterSNN status**: Explicitly `not_applicable_no_pada3dacb_concept_head` (D-16-06). Not treated as failed/incomplete. Confirmed.

7. **Correlation unavailable handling**: Explicit `UNAVAILABLE` status with reasons (D-16-08, metric_protocol.md Section 8). No zero replacement. Confirmed.

6. **Weighted vs unweighted anatomy**: Separate reporting required (D-16-09). Confirmed.

7. **Real-run gate**: `authorized: false` by default (D-16-10). Confirmed.

8. **File ownership**: `agent_plan.yaml` ownership validation shows 13 actions, 0 duplicate paths. Confirmed.

9. **Manuscript scores fallback**: Transparent metrics implemented as fallback (D-16-18). Confirmed.

### Round 2 — BLOCKED
The second review confirmed the first corrections and identified:

1. **Causal terminology**: Confirmed prohibited in schemas, tables, figures, docs. D-16-12 enforced.
2. **AAGN/FasterSNN handling**: Correctly filtered in discovery.py, reported as not-applicable. Confirmed.
3. **Bootstrap unit enforcement**: Confirmed subject-level only, no ROI/fold bootstrapping.
4. **Correlation unavailable handling**: Explicit status/reason in schemas, no zero replacement. Confirmed.
5. **Ownership validation**: 13 actions, 0 duplicate paths. Confirmed.

### Round 3 — PASS
All concerns addressed. Specification approved for implementation.

---

## Approved contracts

### Tensor contracts
- **concepts** (`c_hat`): `[B, K]`, sigmoid-normalized `[0,1]`, predicted tissue-loss proxy per ROI
- **c_target**: `[B, K]`, same normalization, ground-truth tissue-loss proxy
- **g_bar**: `[B, K]`, canonical anatomical reference per ROI
- **alpha**: `[B, K]`, softmax weights, `Σ_k alpha_k ≈ 1`
- **latent_logits/concept_logits**: `[B, 3]`, raw diagnosis logits
- **latent_probs/concept_probs**: `[B, 3]`, softmax probabilities
- **K validation**: Must match atlas metadata and ROI-order hash

### Aggregation contracts
- **Source validation**: True out-of-fold, each subject once per method/seed
- **Target evaluation**: Fold-ensemble per subject (mean concepts, mean probabilities, mean alpha as descriptive); c_target/g_bar immutable
- **Multiple seeds**: Fold-first within seed, then per-seed records retained
- **No pooling**: Directions separate; repeated folds/seeds not independent subjects

### Metric contracts
- **Concept fidelity**: MAE/RMSE/bias (global, per-subject, per-ROI) + Pearson/Spearman with unavailable handling
- **Anatomical consistency**: Same structure; separate unweighted descriptive + canonical weighted
- **Head agreement**: Predictive metrics, top-1 agreement, JS divergence, consistency direction, per-class disagreement
- **ROI stability**: Pairwise Spearman, mean pairwise, std, top-k Jaccard, rank dispersion
- **Class profiles**: Descriptive means + bootstrap CIs per CN/MCI/AD
- **Method comparisons**: Paired subject bootstrap + Holm correction by direction/checkpoint/metric family

### Statistical contracts
- **Bootstrap**: Subject-level, stratified by diagnosis, 10k replicates, explicit seed
- **No ROI bootstrapping**, no fold bootstrapping before subject aggregation
- **Holm**: 6-slot families by direction × checkpoint × metric family
- **Unavailable**: Explicit status + reason; never zero

### Provenance contracts
- 14 validation fields per candidate
- Concept-normalizer hash, atlas ROI-order hash required
- `authorized: false` by default
- Real run fails if unauthorized or hashes null

### Phase boundaries
- No training imports/invocation (D-16-05)
- No gradients (NFR-01)
- No normalizer refitting
- No concept/Jacobian recomputation
- No subject reassignment
- No Phase 17 code

### Manuscript scores
- CFS, ACS, PCS, QIS: **BLOCKED** — no verifiable equations in authoritative sources
- Transparent fallback metrics implemented per requirements
- Will not be invented from names alone

---

## Scope verification

| Requirement | Status |
|---|---|
| Only source_validation and target_evaluation used | ✅ |
| No target-adaptation loader exists | ✅ |
| Subject-level fold/seed aggregation valid | ✅ |
| ROI order and normalizer provenance validated | ✅ |
| Concept fidelity metrics reference-correct | ✅ |
| Anatomy metrics reference-correct | ✅ |
| Head agreement separated from concept fidelity | ✅ |
| ROI stability descriptive and non-causal | ✅ |
| AAGN/FasterSNN reported as not applicable | ✅ |
| Target results select no model/checkpoint | ✅ |
| All previous methods and Phase 15 pass regression | ✅ |
| Full pytest passes | ✅ |
| Ruff passes | ✅ |
| git diff passes | ✅ |
| No training behavior changes | ✅ |
| No concept interventions exist | ✅ |
| No Phase 17 code exists | ✅ |

---

## Final disposition

**Specification approved for implementation.**

Implementation may begin with action `implement-concept-discovery-and-inference` (codex agent) per the action graph dependencies.

---

*Independent review completed by fresh context. All evidence verified against current specification files in `specs/phase_16_concept_validation/`*