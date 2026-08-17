# Binary Evaluation Protocol

**Status:** Specification only; no evaluation has run and no metric is claimed.

## Evaluation population

Evaluation requires an approved binary manifest and a subject-disjoint partition. OASIS evaluation remains blocked until canonical semantics and provenance are approved. Target evaluation labels may be used for evaluation only, never for target adaptation. No real manifest, split hash, class count, or result is supplied here.

## Label and confusion orientation

Use fixed IDs `CN=0` and `Impaired=1` and a 2x2 matrix:

```text
                     predicted CN   predicted Impaired
true CN                   TN                FP
true Impaired             FN                TP
```

`Impaired` is the primary positive class. The matrix order must be serialized with every future result rather than inferred from labels or alphabetical order.

## Probability validation

Future prediction and evaluation validators use the same deterministic policy:

- float64: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-6`;
- float32: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-5`.

Both probabilities must be finite and within `[0,1]`. Argmax uses `[prob_cn, prob_impaired]`; an exact tie selects lower class index `CN=0`. Active `prob_mci` or `prob_ad` fields are rejected. Original diagnosis fields may remain only as provenance.

## Required metrics and undefined values

The future evaluator must report:

- accuracy;
- precision for `Impaired`;
- recall/sensitivity for `Impaired`;
- F1 for `Impaired`;
- AUC-ROC using `prob_impaired`;
- source-validation macro-F1 as the sole best-checkpoint selection criterion.

If a denominator or required class support is zero, the metric is `null` with a machine-readable reason. No undefined metric is silently coerced to zero, one, or another finite value. The same policy applies to all binary metrics and is serialized in evaluation metadata.

Concept macro-F1 remains a separate unchanged concept-space measure and does not replace binary task metrics. Concept targets, atlas/ROI identity, and normalizer contracts remain unchanged.

## Checkpoint, loss, and identity requirements

Any future binary checkpoint must represent two raw logits shaped `(B,2)` with integer targets `{0,1}` consumed by PyTorch-style `CrossEntropyLoss`; `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are not permitted. Evaluation blocks on a one-class partition, missing provenance, incompatible checkpoint, unresolved OASIS semantics, invalid split, or schema mismatch. A future result binds binary task/version, class order, mapping provenance, split identity, checkpoint identity, schema version, and metric policy. Experiment, split, model/checkpoint, training metadata, evaluation result, and freeze identities are each binary-bound and must reject historical three-class collisions.

## Blocking and non-claims

This document defines future behavior only. No training, inference, evaluation, publication analysis, result, or independent review/gate pass has occurred.
