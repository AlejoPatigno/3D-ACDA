# Phase 18B Binary Label Space Requirements

**Status:** Planning specification. No implementation, real execution, publication analysis, native lifecycle operation, review pass, or gate pass is claimed.

## 1. Scope and authorization boundary

Phase 18B defines the publication task `CN` versus `Impaired`. Before OASIS semantics are verified and both fresh independent fallback reviews pass the complete checklist, only documentation, specification maintenance, and synthetic contract-test planning are permitted. That work must not be called implementation.

Production implementation, OASIS mapping, real cohort execution, real split/hash generation, publication results or claims, Phase 19 execution, native lifecycle claims, receipt edits, and `.git/gentle-ai` edits remain forbidden.

The bounded state MUST remain:

```yaml
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

Kimi and Gemini CLI are unavailable. `fallback-review-1` and `fallback-review-2` are fresh independent substitutions, recorded as non-authorizing and pending. Each must pass this same checklist before the review gate can pass. No pass is claimed.

## 2. Normative requirements

### R1. Fixed binary vocabulary

The task MUST expose exactly two task labels in fixed order:

| Numeric ID | Task label |
|---:|---|
| 0 | `CN` |
| 1 | `Impaired` |

The order MUST be declared and MUST NOT be derived alphabetically, from observed data, or from framework ordering.

### R2. Preserve diagnostic provenance

Every included record with a derived binary label MUST retain original cohort diagnosis, mapping provenance, source/cohort, subject identity, and source-row/visit identity. A derived label without original source provenance MUST fail closed. Grouping MCI and AD under `Impaired` is a task grouping, not diagnostic equivalence.

### R3. Fixed ADNI mapping and rejection

Only canonical ADNI labels are supported:

| Original diagnosis | Binary task label | Numeric ID |
|---|---|---:|
| `CN` | `CN` | 0 |
| `MCI` | `Impaired` | 1 |
| `AD` | `Impaired` | 1 |

Missing, unknown, malformed, unsupported, and out-of-domain diagnoses MUST be rejected. Duplicate subject records and conflicting subject diagnoses MUST be excluded from the approved cohort pending explicit duplicate/longitudinal policy. No precedence, recency, majority vote, filename, observed order, or other guess is allowed.

### R4. OASIS semantics are a hard blocker

The repository evidence is:

- `configs/data/oasis.yaml` has `root: null` and `metadata_csv: null`;
- no approved real OASIS manifest is present for this specification;
- legacy `load_oasis_label_map` requires an ID/Subject ID-compatible field and `CDR`, skips missing `CDR`, maps `CDR == 0` to historical `CN`, and maps every other numeric CDR to historical `AD`.

This loader behavior is evidence only. It MUST NOT become final binary semantics. No OASIS record may enter an approved binary production cohort until maintainers approve canonical metadata and generation provenance, including identifier, source fields, accepted values, missing/out-of-domain policy, duplicate/conflict/longitudinal policy, and derivation mapping. No OASIS MCI category may be invented.

Until approval, ambiguous, unsupported, missing, malformed, conflicting, or out-of-domain OASIS values MUST be rejected or excluded and MUST NOT default to `Impaired`.

### R5. Split identity and disposition

The default disposition MUST be `REGENERATE_BINARY_SPLITS_REQUIRED`. Existing assignments may be reused only after evidence proves binary validity, cohort membership, subject-level leakage protection, binary stratification, target partition separation, complete provenance, and deterministic identity compatibility. No real split manifest, split hash, class count, or binary freeze is claimed here.

Six future identity families—experiment, split, model/checkpoint, training metadata, evaluation result, and freeze—MUST each bind binary task/version, class order, mapping provenance, and relevant inputs. Each MUST reject collision with a historical three-class identity.

### R6. Classifier, adaptation, and loss contracts

Binary task classifier heads MUST emit two raw logits with shape `(B,2)` and integer class targets in `{0,1}` consumed by PyTorch-style `CrossEntropyLoss`. This MUST NOT use `BCEWithLogitsLoss`, sigmoid, or one-logit BCE. Concept outputs and concept artifacts MUST remain `(B,K)`; `K`, ROI order, atlas identity, concept targets, and normalizer are unchanged.

CDAN conditioning dimension MUST be computed at runtime as `z_dim*n_classes`. Contract-only tests MUST cover `(z_dim,n_classes)=(128,2)->256` and a distinct configuration such as `(64,2)->128` (or `(128,3)->384`). A backward-gradient test MUST show gradients reach both `z` and `p`; no detach is permitted.

Prototype class IDs and pseudo-label targets MUST be integer `{0,1}`; prototype and pseudo-label logits MUST be raw `(B,2)` logits consumed by the same PyTorch-style `CrossEntropyLoss`. Contract tests MUST cover absent class 0 and absent class 1 independently. Accepted pseudo rows MUST use `CrossEntropyLoss`; an empty accepted set MUST return zero loss; `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are prohibited. Target diagnosis and target binary labels MUST be rejected from adaptation inputs.

CORAL and MMD mathematics MUST remain unchanged.

### R7. Checkpoint compatibility

A binary classifier loader MUST reject a checkpoint whose classifier cardinality is not two before loading any parameters. Historical three-class checkpoints MUST fail closed. Partial loading, classifier-key omission, weight subsetting, truncation, or warning-only recovery MUST NOT bypass the mismatch.

### R8. Preserved training and architecture invariants

Unless separately approved, the migration MUST preserve fixed epoch counts, continued training after best-checkpoint saves, source-validation macro-F1 as the only best-checkpoint selection criterion, target-label firewall, disjoint target partitions, ROI order, atlas/artifact identity, concept normalizer and targets, tokenizer/preprocessing/attention/anatomical contracts, approved CORAL/MMD equations, and protected output/provenance behavior.

### R9. Prediction and evaluation contract

The binary prediction schema MUST identify `prob_cn` for ID 0 and `prob_impaired` for ID 1. Active legacy fields `prob_mci` and `prob_ad` MUST be rejected. Original diagnosis fields may remain only as provenance.

Probabilities MUST be finite and in `[0,1]`, with the same deterministic normalization policy everywhere: float64 tolerance `1e-6`, float32 tolerance `1e-5`. Argmax ties MUST select lower class index `CN=0`.

Evaluation MUST use a 2x2 confusion matrix with true rows and predicted columns in `[CN, Impaired]` order. `Impaired` is primary positive. Accuracy, precision, recall/sensitivity, F1, and AUC-ROC MUST use an explicit undefined-value policy; zero support or denominator MUST produce `null` plus a reason, never silent coercion. Source-validation macro-F1 remains the checkpoint-selection criterion.

### R10. CN-versus-AD sensitivity is specification-only

A secondary sensitivity protocol MAY use original diagnosis provenance, but it MUST NOT be executed or reported as a result in this phase. It MUST include original `CN` and original `AD`, exclude original `MCI` and unresolved/ambiguous/conflicting/unsupported records, define AD as positive, and emit no publication result here.

### R11. Historical artifact supersession

Historical Phase 18 three-class planning identities, matrices, split manifests, checkpoints, and hashes MUST remain unchanged and preserved. New Phase 18B artifacts MUST identify conceptual supersession with:

`SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`

Historical files MUST NOT be edited, regenerated, deleted, or merged with binary outputs.

### R12. Fail-closed authorization and review gates

Production implementation MUST remain blocked until OASIS semantics are verified and both substituted independent reviews pass the same complete checklist. Fallback review substitution is recorded because Kimi and Gemini CLI are unavailable; neither fallback is currently authorizing and no pass is claimed.

No action marked complete in inherited artifacts is accepted as evidence of implementation, testing, review, or execution. Statuses MUST remain planning, pending, or blocked unless they merely record specification text written in this package.

## 3. Resolved decisions

- Primary task: binary `CN` versus `Impaired`.
- Fixed IDs: `CN=0`, `Impaired=1`.
- ADNI mapping: `CN→CN`, `MCI→Impaired`, `AD→Impaired`; invalid values reject; duplicate/conflicting subjects exclude pending policy.
- OASIS: blocked; legacy behavior is evidence only; ambiguous values reject/exclude.
- Split disposition: `REGENERATE_BINARY_SPLITS_REQUIRED` unless exact validity is proven later.
- Three-class checkpoints: incompatible and rejected without partial loading.
- Classifier logits: two; CDAN runtime dimension with required distinct configuration and gradient checks; concepts remain `(B,K)`.
- Prototype/pseudo paths: two raw logits `(B,2)`, integer targets/IDs `{0,1}`, PyTorch-style `CrossEntropyLoss`, absent-class cases, empty accepted set zero loss, and no target diagnosis; `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are prohibited.
- Probabilities: shared float64/float32 tolerances and lower-index CN tie-break.
- Metrics: undefined values are `null` plus reason.
- Active `prob_mci` and `prob_ad` fields are rejected.
- Six binary identity families reject historical three-class collisions.
- Target adaptation remains label-free; CORAL/MMD and protected invariants remain unchanged.
- Execution/publication/freeze flags remain false; Phase 19 remains forbidden.

## 4. Repository evidence

Evidence recorded for this specification is limited to repository text and the supplied authoritative proposal. No real data was read or processed. OASIS configuration and legacy loader facts are recorded in `cohort_semantics.md`; they are not approval of OASIS semantics.

## 5. Unresolved decisions and blocked gates

1. Canonical OASIS manifest and metadata-generation provenance.
2. Approved OASIS source fields, value domain, missing/out-of-domain, duplicate/conflict, and longitudinal policy.
3. Deterministic binary split parameters and identities after cohort approval.
4. Exact versioned schema/hash migration details for production artifacts.
5. Two substituted independent specification reviews.

## 6. Permitted planning and future tests

Before the gates pass, only documentation, specification refinement, and planning of synthetic contract tests are allowed; none is implementation. Future tests cover label mapping, provenance, deterministic rejection, target-label firewall, shape/cardinality, CDAN configurations and gradients, prototype/pseudo absent classes and empty sets, checkpoint rejection, prediction tolerance/tie/legacy-field rejection, evaluation null policy, six identity collisions, split validation, and authorization flags. No such implementation or test has been run or passed in this package.
