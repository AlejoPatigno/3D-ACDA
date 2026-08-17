# Binary Prediction Schema

**Status:** Specification only; no predictions have been generated.

## Fixed probability fields

Each binary prediction record must expose these active probability fields in fixed class order:

| Field | Class ID | Meaning |
|---|---:|---|
| `prob_cn` | 0 | Probability of `CN` |
| `prob_impaired` | 1 | Probability of `Impaired` |

Active legacy fields `prob_mci` and `prob_ad` are rejected. Original diagnosis fields may be retained only as provenance; they are not active prediction fields and must never be reinterpreted as binary probabilities.

The two active probabilities must be finite, within `[0,1]`, and satisfy the shared deterministic normalization policy:

- float64: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-6`;
- float32: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-5`.

The declared dtype selects the tolerance. Other dtypes are rejected unless a future contract explicitly defines one. The predicted task label is argmax over `[prob_cn, prob_impaired]`; an exact tie deterministically selects the lower class index, `CN=0`.

No historical three-class probability field may be silently reinterpreted as binary. Prediction metadata must identify the binary task, class order, schema version, subject identity, cohort, and provenance needed to audit the record. Target adaptation records must not receive target labels.

## Confusion matrix contract

The evaluation schema uses:

```text
rows    = true [CN, Impaired]
columns = predicted [CN, Impaired]
shape   = 2 x 2
positive class = Impaired
```

The matrix and metrics must carry class order explicitly so consumers cannot infer orientation from labels or alphabetical order.

## Metric failure behavior

Accuracy, precision, recall/sensitivity, F1, and AUC-ROC use one shared undefined-value policy. If a denominator or required class support is zero, the result is `null` plus a machine-readable reason. No undefined value is silently coerced to zero, one, or another finite value.

## Compatibility and failure behavior

Reject records with missing active probability fields, active `prob_mci` or `prob_ad`, extra legacy class cardinality, non-finite values, out-of-range values, invalid normalization, inconsistent class order, or incompatible task identity. Do not coerce a three-class output into this schema.

## Secondary sensitivity slice

The CN-versus-AD sensitivity protocol uses original diagnosis provenance to filter records; it is not a second prediction schema and is specification-only. It excludes MCI and unresolved, ambiguous, conflicting, or unsupported labels and emits no result in this phase.
