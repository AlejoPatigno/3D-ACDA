# Phase 15 Statistical Protocol

## Protocol identity

`protocol_version: phase15-statistical-v2`

This document is normative. The subject is the statistical unit. All arrays and metric inputs MUST be NumPy `float64`; labels MUST be explicit integers with fixed order `(CN,MCI,AD)=(0,1,2)`. Directions and checkpoint policies are separate analyses.

## 1. Subject ensemble

For validated target probability `p[i,f,s,k]` of stable `subject_hash=i`, source fold `f`, predeclared seed `s`, and class `k`:

`p_seed[i,s,k] = (1/F) sum_f p[i,f,s,k]`

`p_final[i,k] = (1/|S|) sum_s p_seed[i,s,k]`

Every subject MUST have exactly one row for every required fold within every required seed. Every configured seed MUST enter the final mean. Missing or duplicate rows invalidate the method-direction-policy. `y_hat[i]` is the smallest fixed-order index attaining `max_k p_final[i,k]`. Source OOF data MUST have exactly one row per subject/method/direction/seed/logical checkpoint and MUST NOT be fold-averaged. Directions and logical checkpoints MUST NOT be pooled.

One true label per `subject_hash` MUST agree across all folds, seeds, methods, and checkpoint policies in a direction. Disagreement is `inconsistent_true_label` and blocks affected evaluation and pairing.

## 2. Complete metric definitions

Let `C=3`, `N` be subject count, `TP_k,FP_k,FN_k,TN_k` be fixed-label one-vs-rest counts, and `n_k=TP_k+FN_k`. Metric values MUST be finite or null.

### 2.1 Per-class metrics

The evaluator MUST compute seven distinct per-class statistical quantities and MUST emit eight named rows because `recall` and `sensitivity` are numerically identical aliases. The seven quantities are support, precision, recall/sensitivity, specificity, F1, OVR ROC-AUC, and OVR average precision.

| Metric | Exact definition | Unavailable when / reason |
|---|---|---|
| Support | `n_k` | available as integer when table exists; otherwise `empty_subject_set` |
| Precision | `TP_k/(TP_k+FP_k)` | denominator zero / `no_predicted_positive` |
| Recall / sensitivity | `TP_k/n_k` | `n_k=0` / `missing_true_class` |
| Specificity | `TN_k/(TN_k+FP_k)` | denominator zero / `missing_negative_class` |
| F1 | `2TP_k/(2TP_k+FP_k+FN_k)` | denominator zero / `zero_f1_denominator` |
| ROC-AUC OVR | trapezoidal ROC AUC of `I(y=k)` against `p[:,k]` | no positive / `missing_true_class`; no negative / `missing_negative_class` |
| Average precision OVR | `sum_n (R_n-R_{n-1})P_n` from scikit-learn's non-interpolated binary precision-recall sequence for `I(y=k)` and `p[:,k]` | no positive / `missing_true_class`; no negative / `missing_negative_class` |

### 2.2 Aggregate metrics

| Metric | Exact definition | Availability |
|---|---|---|
| Accuracy | `sum_i I(y_i=y_hat_i)/N` | unavailable if `N=0` |
| Balanced accuracy | `(1/3)sum_k recall_k` | unavailable if any recall is unavailable |
| Macro-F1 | `(1/3)sum_k F1_k` | unavailable if any F1 is unavailable |
| Weighted F1 | `sum_{k:n_k>0}(n_k/N)F1_k` | unavailable if `N=0` or any positive-support class F1 is unavailable; zero-support classes have exact weight zero |
| Macro precision | `(1/3)sum_k precision_k` | unavailable if any precision is unavailable |
| Macro recall | `(1/3)sum_k recall_k` | unavailable if any recall is unavailable; numerically equal to balanced accuracy but emitted separately |
| Multiclass MCC | scikit-learn multiclass Matthews correlation coefficient using fixed labels | unavailable if standard multiclass denominator is zero / `zero_mcc_denominator` |
| Cohen's kappa | `(p_o-p_e)/(1-p_e)`, `p_o=accuracy`, `p_e=sum_k(n_k/N)(predicted_count_k/N)` | unavailable if `N=0` or `1-p_e=0` / `zero_kappa_denominator` |
| Multiclass log loss | `-(1/N)sum_i log(q[i,y_i])`, with clipping/renormalization below | unavailable if `N=0`, invalid probability, or non-finite result |
| Multiclass Brier score | **unscaled** mean class sum: `(1/N)sum_i sum_{k=0}^2 (p[i,k]-I(y_i=k))^2`; range `[0,2]`; MUST NOT divide by class count | unavailable if `N=0`, invalid probability, or non-finite result |
| Macro ROC-AUC OVR | arithmetic mean of all three per-class OVR ROC-AUC values | unavailable if any class AUC is unavailable |
| Macro average precision OVR | arithmetic mean of all three per-class OVR AP values | unavailable if any class AP is unavailable |

### 2.3 Log-loss clipping and library behavior

Validated probabilities enter as `float64`, finite, in `[0,1]`, with row sum within `1e-6` of one. Before log loss only, set `eps=np.finfo(np.float64).eps`, compute `q=clip(p,eps,1-eps)`, then renormalize every row as `q_i=q_i/sum_k q_i,k`. The emitted value MUST equal `sklearn.metrics.log_loss(y_true,q,labels=[0,1,2],normalize=True)`. No library-default epsilon, inferred labels, or unrecorded normalization is allowed. Other metrics use original validated `p_final`, not clipped `q`.

### 2.4 Status contract

Every metric record MUST include `value,status,reason`. For metric records, `available` requires a finite non-null value and null reason; `unavailable` requires a null value and a stable protocol metric-unavailability reason. Undefined values MUST NOT be coerced to zero. Inferential records likewise MUST use null reason when `available` and MAY carry a separate optional `note_code` for non-error information. Protocol metric-unavailability reasons are a separate namespace from candidate `IssueCode` tokens and MUST NOT be used as candidate issue codes. In addition to reasons above, allowed metric-unavailability reasons are `empty_subject_set`, `non_finite_input`, `probability_out_of_range`, `probability_sum_invalid`, `incomplete_ensemble`, `incompatible_subjects`, and `insufficient_valid_bootstrap_replicates`.

## 3. Established-library policy and reference tests

Released, exact-version-recorded APIs MUST provide or independently verify results:

- scikit-learn: `accuracy_score`; `balanced_accuracy_score`; `precision_score`, `recall_score`, `f1_score` with `labels=[0,1,2]` and explicit averaging; `matthews_corrcoef`; `cohen_kappa_score(labels=[0,1,2])`; `log_loss` as Section 2.3; `roc_auc_score` per fixed one-vs-rest class; `average_precision_score` per fixed one-vs-rest class; `confusion_matrix(labels=[0,1,2])`;
- SciPy: `binomtest` for exact McNemar;
- NumPy: float64 formulas, `Generator(PCG64(seed))`, and quantiles with `method="linear"`;
- statsmodels: `multipletests(...,method="holm")` verification.

The implementation MUST check availability before aggregate library calls and MUST NOT rely on `zero_division=0`, warnings, inferred class order, or library omission of absent labels. Deterministic reference tests MUST compare all twelve aggregate metrics and seven distinct per-class statistical quantities emitted as eight named rows against direct formulas and the specified library calls, including clipping, unscaled Brier score, missing classes, no predicted positives, and float64 dtype. Exact library versions belong to evaluation identity.

## 4. Confusion matrices

`M[r,c]=count(y=r,y_hat=c)` is 3x3, rows true and columns predicted in `(CN,MCI,AD)` order. `R[r,c]=M[r,c]/sum_c M[r,c]`. A zero-support row in `R` MUST contain three nulls with `status=unavailable,reason=zero_true_support`; `M` retains integer zeros. Both CSVs and PNGs MUST be derived only from the final canonical subject table for that exact method/direction/policy.

## 5. Stratified subject bootstrap

Default `B=10000`; `B>0`; explicit seed required. Within each true class, sample with replacement exactly its observed count; concatenate strata in fixed class order. Draw each replicate once. Undefined metric replicates are invalid for that metric and MUST NOT be redrawn.

For metric `m`, record `requested=B`, `successful=S_m`, `invalid=B-S_m`. The 95% percentile interval is NumPy linear quantiles `[0.025,0.975]` over successful values. CI is available only if `S_m>=ceil(0.95B)`; otherwise limits are null with `insufficient_valid_bootstrap_replicates`. This applies to every aggregate metric in Section 2.2.

## 6. Exact paired McNemar

For prototype `P` and comparator `C` on identical ordered `subject_hash` and labels: `n00` both wrong, `n01` P correct/C wrong, `n10` P wrong/C correct, `n11` both correct. Let `d=n01+n10`. Use only two-sided exact McNemar: if `d=0`, emit `status=available`, `p_raw=1.0`, `reason=null`, and `note_code=no_discordant_pairs`; otherwise `p_raw=scipy.stats.binomtest(k=n01,n=d,p=0.5,alternative="two-sided").pvalue`, equivalently `min(1,2*BinomCDF(min(n01,n10);d,0.5))`, with `status=available`, `reason=null`, and absent/null `note_code`. No continuity correction or asymptotic fallback.

## 7. Paired stratified bootstrap differences

Paired inference metrics remain the predeclared accuracy, balanced accuracy, macro-F1, MCC, and macro ROC-AUC. Prototype and comparator MUST have identical ordered `subject_hash` sets and labels. One stratified index vector is applied to both methods per replicate.

`delta_observed=m(prototype_pseudo)-m(comparator)` and `delta_b=m_b(prototype_pseudo)-m_b(comparator)`. Positive favors prototype. A replicate succeeds only if both values and difference are finite; no redraw. CI is the raw-difference 95% percentile interval and requires `S>=ceil(0.95B)`. Define `delta0_b=delta_b-delta_observed`; the two-sided plus-one p-value is `(1+count(|delta0_b|>=|delta_observed|))/(S+1)`. It is unavailable if the observed metric or success threshold is unavailable.

## 8. Holm correction

Each family contains exactly the six predeclared prototype comparisons against `source_only,coral,mmd,cdan,aagn,faster_snn`, in that tie-break order. Families are separate by direction, checkpoint policy, and statistic: one `mcnemar_accuracy` family and one for each paired-bootstrap metric. Family size remains six when hypotheses are unavailable. Available p-values sort ascending; canonical comparator order breaks ties. At rank `j`, `q_j=(6-j+1)p_(j)` and `p_adj(j)=min(1,max_{l<=j}q_l)`. Unavailable rows retain null raw/adjusted p-values and do not reduce six. Report raw and adjusted values. No automatic all-pairs.

## 9. Gates and boundaries

No real statistic may be computed until complete authorized exports, D-14-001 resolution, D-14-002 resolution, and independent protocol approval are hash-bound. Synthetic outputs are `synthetic_test_only`. No training, target-guided selection, concept evaluation, manuscript generation, or Phase 16 work is authorized.
