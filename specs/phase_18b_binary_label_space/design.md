# Phase 18B Binary Label Space Design

**Status:** Planning only. This is a proposed contract design, not evidence that code, tests, review, gates, or production execution exists.

## Design outcome

Define a versioned binary task contract without mutating historical Phase 18 artifacts. Before the OASIS semantics gate and two substituted independent checklist reviews pass, the package permits only documentation, specification maintenance, and synthetic contract-test planning. No production implementation may start in that interval.

## Flow

```text
source record
  -> canonical source-label validation
  -> approved cohort mapping
  -> provenance-preserving binary record
  -> binary split identity and partition validation
  -> model/task compatibility validation
  -> binary prediction schema
  -> binary evaluation schema
```

OASIS stops at source-label validation until its canonical manifest and metadata-generation provenance are approved. No final OASIS mapping behavior may be encoded from the legacy loader.

## Label boundary

```yaml
class_order: [CN, Impaired]
class_ids:
  CN: 0
  Impaired: 1
adni:
  CN: CN
  MCI: Impaired
  AD: Impaired
```

Only canonical ADNI labels are accepted. Missing, unknown, malformed, unsupported, and out-of-domain values are rejected. Duplicate subjects and subjects with conflicting diagnoses are excluded pending explicit policy. No source diagnosis is guessed. The record retains `original_label_name`, `binary_label_name`, `binary_label`, cohort, subject identity, source-row/visit identity, and mapping provenance.

## Cohort gateway

### ADNI

The mapping is deterministic and preserves MCI versus AD in original provenance. A derived label without original provenance is invalid. Duplicate and conflicting subjects do not enter the approved cohort until an explicit policy is approved.

### OASIS

The repository has null OASIS root and metadata paths. The legacy `load_oasis_label_map` behavior is evidence only: it requires an ID-compatible field and CDR, skips missing CDR, maps zero CDR to historical CN, and maps all other numeric CDR to historical AD. It is not scientific binary semantics.

The future gateway requires approval of canonical metadata, identifier, source fields, accepted values, missing/out-of-domain policy, duplicate/conflict/longitudinal policy, and derivation provenance. Until then, missing, ambiguous, unknown, malformed, conflicting, and out-of-domain cases are rejected or excluded; no OASIS MCI is invented and no case defaults to `Impaired`.

## Split and identity boundary

Binary split generation is a new identity namespace. The default state is `REGENERATE_BINARY_SPLITS_REQUIRED`. Reuse requires proof of binary cohort validity, subject-level disjointness, leakage protection, stratification, target-partition separation, deterministic parameters, complete manifest coverage, and artifact compatibility.

Six identity families must each bind binary task/version, class order, mapping provenance, and their relevant inputs: experiment, split, model/checkpoint, training metadata, evaluation result, and freeze. Each must reject collision with a historical three-class identity. No real identity or hash is created here.

## Model, adaptation, and loss boundary

Task classifier heads emit two raw logits shaped `(B,2)` with integer targets `{0,1}`, consumed by PyTorch-style `CrossEntropyLoss`. This is not `BCEWithLogitsLoss`, sigmoid, or one-logit BCE. Concept outputs remain `(B,K)` and concept artifacts, atlas identity, ROI order, and normalizer remain unchanged. CDAN computes conditioning width at runtime as `z_dim*n_classes`; contract-only cases include `(128,2)->256` and `(64,2)->128`, with backward gradients reaching both `z` and `p` and no detach. CORAL and MMD remain unchanged.

Prototype and pseudo-label paths use two raw logits shaped `(B,2)`, integer targets and prototype IDs `{0,1}`, and PyTorch-style `CrossEntropyLoss`. Tests cover an absent class 0 and an absent class 1, an empty accepted set returns zero loss, and no target diagnosis or target label is consumed. `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are prohibited.

Target adaptation receives no target diagnosis or binary label. `target_adaptation` and `target_evaluation` partitions remain disjoint.

## Checkpoint boundary

Checkpoint metadata identifies task vocabulary, class order, classifier cardinality, and task identity. A loader validates task/cardinality compatibility before loading. A three-class checkpoint is rejected before any parameter load; partial loading, classifier omission, and truncation are prohibited.

## Prediction and evaluation boundary

Predictions use only `prob_cn` and `prob_impaired` in fixed order. Active `prob_mci` and `prob_ad` fields are rejected. Original diagnosis fields may remain only as provenance. Float64 probabilities must satisfy sum tolerance `1e-6`; float32 uses `1e-5`. Argmax ties select lower class index CN. Evaluation uses one shared tolerance and undefined-metric policy: zero support yields `null` plus a reason, never coercion. Confusion is 2x2 with true rows, predicted columns, and `Impaired` positive. CN-versus-AD sensitivity remains specification-only.

## Historical and authorization boundary

Historical Phase 18 three-class files are immutable. New artifacts may carry `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`; they must not rewrite historical contents. The flags remain `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true`. Receipt `review-1d63ad8511d6bbf5` remains untouched.

## Review substitution and gates

Kimi and Gemini CLI are unavailable. `fallback-review-1` and `fallback-review-2` are fresh independent substitutions, recorded as non-authorizing and pending. They must each pass the same acceptance checklist before the independent-review gate can pass. OASIS semantics remain blocked. No review or gate pass is claimed.

## Future sequence after gates

1. Maintain documentation and synthetic contract-test plans.
2. Obtain both substituted independent checklist passes.
3. Verify and approve OASIS semantics from canonical manifest and provenance.
4. Only then consider production implementation, subject to all safety flags and real-execution prohibitions in force for this package.
