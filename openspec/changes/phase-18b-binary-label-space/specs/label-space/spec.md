# Phase 18B Binary Label Space Normative Specification

**Status:** Planning specification only. No implementation, execution, review pass, gate pass, publication result, or freeze is claimed.

## 1. Authorization and sequencing

This specification permits documentation, specification maintenance, and planning of synthetic contract tests only. It does not authorize production implementation, real data access, OASIS mapping, real splits, training, inference, evaluation, publication analysis, Phase 19 execution, native lifecycle operations, or receipt edits.

Production implementation is permitted only after both prerequisites independently pass:

1. OASIS semantics are verified and approved from a canonical manifest and metadata-generation provenance; and
2. both fresh independent fallback reviews pass the complete Phase 18B checklist: `fallback-review-1` (substituted for unavailable Kimi) and `fallback-review-2` (substituted for unavailable Gemini CLI).

Kimi and Gemini CLI are unavailable in this session. `fallback-review-1` and `fallback-review-2` are therefore recorded as fresh independent substitutions. Each is non-authorizing until it passes the same complete checklist; both review statuses remain pending.

The bounded state MUST remain:

```yaml
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

## 2. Fixed binary contract

The task exposes exactly two labels in this order:

```yaml
class_order: [CN, Impaired]
class_ids:
  CN: 0
  Impaired: 1
```

Class order is explicit and must never be inferred from data, alphabetic order, or framework ordering.

### ADNI

Only these canonical source diagnosis tokens are supported:

```text
CN  -> CN (0)
MCI -> Impaired (1)
AD  -> Impaired (1)
```

The source token must be a canonical, well-formed diagnosis value. Missing, unknown, malformed, unsupported, out-of-domain, or already-derived values are rejected. No filename, observed class order, or other incidental field may be used to guess a diagnosis.

Every duplicate subject record is excluded from the approved cohort pending an explicitly approved duplicate/longitudinal policy. A subject with conflicting diagnoses is likewise excluded; no conflict is resolved by precedence, recency, majority vote, or guessing. Original diagnosis, cohort, subject identity, source-row/visit identity, and mapping provenance remain mandatory for every included derived record.

### OASIS

OASIS production semantics remain blocked pending approval of a canonical manifest and metadata-generation provenance. The approval must define the authoritative identifier, source fields, accepted value domain, missing and out-of-domain policy, duplicate and longitudinal policy, conflict handling, and deterministic mapping to the two classes.

Until approval, missing, ambiguous, unknown, malformed, conflicting, or out-of-domain OASIS values are rejected or excluded and never default to `Impaired`. No OASIS MCI category may be synthesized. The legacy loader is evidence only and cannot satisfy this gate.

## 3. Provenance and label firewall

A derived record without original diagnosis provenance is invalid. Target adaptation inputs contain no target diagnosis, binary label, or target-derived decision. `target_adaptation` and `target_evaluation` subject sets must be disjoint. Target labels may be used only by a separately authorized evaluation contract, never by adaptation.

## 4. Numeric prediction and evaluation contract

Prediction records expose exactly the active binary probability fields:

```text
prob_cn       = class ID 0
prob_impaired = class ID 1
```

Active legacy fields `prob_mci` and `prob_ad` are rejected. Original diagnosis fields may remain only as provenance fields; they are not active prediction fields and must not be reinterpreted as binary probabilities.

Probabilities must be finite and each lie in `[0, 1]`. The normalization rule is deterministic and shared by prediction validation, evaluation, and acceptance:

- float64: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-6`;
- float32: `abs((prob_cn + prob_impaired) - 1.0) <= 1e-5`.

The declared storage dtype selects the corresponding tolerance; other dtypes are rejected unless a future specification adds an explicit tolerance. Predicted class is argmax over `[prob_cn, prob_impaired]`; an exact tie is resolved in favor of the lower class index, `CN=0`.

The confusion matrix is 2x2, with true labels as rows and predicted labels as columns in `[CN, Impaired]` order. `Impaired` is the primary positive class. Accuracy, precision, recall/sensitivity, F1, and AUC-ROC use an explicit undefined-value policy: if a denominator or required support is zero, the metric is reported as `null` with a machine-readable reason; it is never silently coerced to zero, one, or another finite value. Source-validation macro-F1 remains the sole checkpoint-selection criterion.

## 5. Tensor, adaptation, and loss contracts

- Task logits are two raw logits with shape `(B,2)` and integer class targets are in `{0,1}`, consumed by PyTorch-style `CrossEntropyLoss`. This is **not** `BCEWithLogitsLoss`, does not apply sigmoid, and is not one-logit BCE.
- Concept outputs and artifacts remain `(B, K)` with unchanged concept targets, ROI order, atlas identity, and normalizer.
- CDAN conditioning width is computed at runtime as `z_dim * n_classes`. Contract-only tests must cover `(128, 2) -> 256` and a distinct configuration such as `(64, 2) -> 128` (or `(128, 3) -> 384`). The backward-gradient test must show nonzero gradient reaches both feature representation `z` and class-probability input `p`; no detach is permitted.
- Prototype class IDs and pseudo-label targets are exactly `{0,1}`; prototype and pseudo-label logits are two raw logits shaped `(B,2)` and use PyTorch-style `CrossEntropyLoss`. Tests must cover absent class 0 and absent class 1 independently. Accepted pseudo rows use the same `CrossEntropyLoss`; an empty accepted set returns zero loss, and no target diagnosis or target binary label is consumed. `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are not permitted.
- CORAL and MMD equations and weighting semantics remain unchanged.
- A three-class checkpoint is rejected before loading with an explicit cardinality error. Partial loading, classifier-key omission, truncation, and warning-only recovery are prohibited.

## 6. Binary identity contract

Future identities for each of the following must be independently binary-bound and collision-checked:

- experiment;
- split;
- model/checkpoint;
- training metadata;
- evaluation result;
- freeze.

Each identity binds the binary task/version, fixed class order, mapping provenance, and the relevant configuration, manifest, split, checkpoint, or result inputs. Contract tests must assert that each binary identity is distinct from its historical three-class counterpart and that a historical three-class collision is rejected. No real identity, hash, split, result, or freeze is created by this package.

## 7. Split and sensitivity boundaries

The default split disposition is exactly `REGENERATE_BINARY_SPLITS_REQUIRED`. Reuse requires proof of binary cohort validity, subject-level leakage protection, stratification, partition separation, complete provenance, and identity compatibility. OASIS splits remain blocked with OASIS semantics.

The CN-versus-AD sensitivity protocol is specification-only. It includes original `CN` and original `AD`, excludes original `MCI` and every unresolved/ambiguous/conflicting record, defines original AD as positive, and cannot emit a result in this phase.

## 8. Historical protection and supersession

Historical Phase 18 three-class artifacts remain unchanged. Only new Phase 18B artifacts may carry:

`SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`

That marker is additive and does not authorize rewriting, deleting, regenerating, or merging historical artifacts.

## 9. Acceptance evidence boundary

This package records requirements and future contract-test planning only. No implementation, test pass, independent review pass, OASIS gate pass, real execution, publication analysis, native lifecycle validation, receipt mutation, or binary freeze is claimed.
