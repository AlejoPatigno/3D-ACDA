# Phase 18B Binary Label Space Acceptance

**Acceptance status:** Not accepted. This is a future gate definition; no criterion below is claimed passed.

## Gate order and authorization

Only documentation, specification maintenance, and synthetic contract-test planning are permitted before both gates pass. Calling that work implementation is prohibited. No production implementation may start until both gates independently pass:

1. **OASIS semantics gate:** maintainers verify and approve the canonical OASIS manifest and metadata-generation provenance, including identifier, source fields, accepted values, missing-value policy, duplicate/longitudinal policy, conflict policy, and unambiguous mapping.
2. **Independent specification review gate:** fresh independent reviewers apply this complete checklist and return pass evidence.

Kimi and Gemini CLI are unavailable in this session. `fallback-review-1` and `fallback-review-2` are recorded as fresh independent substitutions. They are non-authorizing and remain pending until each independently passes this same complete checklist; no review pass is claimed.

The OASIS gate blocks production OASIS mapping and real OASIS splits. Real execution, publication analysis, native lifecycle operations, receipt edits, and Phase 19 remain forbidden.

## Executable acceptance criteria

### A1. Fixed vocabulary and deterministic source policy

- [ ] The contract exposes exactly `CN` and `Impaired`.
- [ ] The contract returns IDs `CN=0` and `Impaired=1` regardless of input ordering.
- [ ] Canonical ADNI labels map only as `CN→CN`, `MCI→Impaired`, and `AD→Impaired`.
- [ ] A test proves MCI and AD remain distinct in `original_label_name`.
- [ ] Missing, unknown, malformed, unsupported, and out-of-domain ADNI labels are rejected.
- [ ] Duplicate subject records and conflicting subject diagnoses are excluded from the approved cohort pending explicit policy; no precedence or guessing is allowed.
- [ ] OASIS remains pending approved policy; ambiguous, unknown, missing, malformed, conflicting, and out-of-domain values are rejected or excluded and never guessed.

### A2. Provenance and firewall

- [ ] Derived records retain original diagnosis, binary name/ID, cohort, subject identity, source-row/visit identity, and mapping provenance.
- [ ] A record with a derived label but no original provenance fails closed.
- [ ] Target adaptation batches contain no target diagnosis or binary label.
- [ ] `target_adaptation` and `target_evaluation` subject sets are disjoint.

### A3. OASIS blocker

- [ ] The validator reports a blocked outcome while the canonical manifest or provenance is absent.
- [ ] Null `root` or `metadata_csv` cannot be treated as an approved data source.
- [ ] Legacy `load_oasis_label_map` behavior is covered as evidence only and is not accepted as final semantics.
- [ ] No OASIS MCI label is synthesized.
- [ ] Ambiguous, unknown, missing, malformed, conflicting, or out-of-domain OASIS values are rejected or excluded under the approved policy.

### A4. Split identity

- [ ] Default disposition is exactly `REGENERATE_BINARY_SPLITS_REQUIRED`.
- [ ] Reuse is rejected without proof of binary cohort validity, stratification, leakage protection, partition separation, and identity compatibility.
- [ ] New binary identity includes task/class-order/mapping provenance and cannot equal a historical three-class identity.
- [ ] Separate collision tests cover experiment, split, model/checkpoint, training metadata, evaluation result, and freeze identities.
- [ ] No real split hash, class count, or binary freeze is asserted by synthetic fixtures.

### A5. Tensor, adaptation, and checkpoint contracts

- [ ] Binary classifier emits two raw logits shaped `(B,2)` with integer targets `{0,1}` consumed by PyTorch-style `CrossEntropyLoss`; this is not `BCEWithLogitsLoss`, sigmoid, or one-logit BCE.
- [ ] Concept outputs and artifacts remain `(B, K)`.
- [ ] CDAN computes conditioning width at runtime as `z_dim*n_classes` and tests `(128,2)->256` plus a distinct configuration such as `(64,2)->128`.
- [ ] A CDAN backward test proves gradient reaches both `z` and `p` with no detach.
- [ ] Prototype labels/logits/class IDs are binary; tests cover absent class 0 and absent class 1.
- [ ] Accepted pseudo rows use the same PyTorch-style `CrossEntropyLoss`; an empty accepted set returns zero loss; `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are rejected; target diagnosis is rejected.
- [ ] CORAL/MMD contract values and equations are unchanged.
- [ ] A three-class checkpoint is rejected before loading with an explicit cardinality error.
- [ ] Partial loading and classifier-key omission are rejected.

### A6. Prediction and evaluation

- [ ] Predictions contain only active binary probability fields `prob_cn` for ID 0 and `prob_impaired` for ID 1.
- [ ] Active legacy fields `prob_mci` and `prob_ad` are rejected; original diagnosis fields may remain only as provenance.
- [ ] Probability values are finite and in `[0,1]`; normalization is `abs((prob_cn + prob_impaired)-1.0) <= 1e-6` for float64 and `<= 1e-5` for float32.
- [ ] Argmax ties deterministically select lower class index `CN=0`.
- [ ] Confusion matrix is 2x2, true labels are rows, predicted labels are columns, and `Impaired` is primary positive.
- [ ] Accuracy, precision, recall/sensitivity, F1, and AUC-ROC use the same explicit undefined-value policy: zero support yields `null` plus a reason, never silent coercion.
- [ ] Source-validation macro-F1 is the only best-checkpoint selection criterion.
- [ ] Concept targets, concept macro-F1, atlas/ROI identity, and normalizer contracts remain unchanged.

### A7. CN-versus-AD sensitivity specification

- [ ] Protocol filters original `CN` and original `AD` only, excludes `MCI` and unresolved/ambiguous/conflicting records, and defines AD as positive.
- [ ] The protocol is specification-only and cannot emit a publication result in this phase.

### A8. Historical and authorization safety

- [ ] New artifacts contain `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE` where historical supersession is discussed.
- [ ] Historical Phase 18 files are unchanged.
- [ ] `freeze_approved`, `real_execution_authorized`, and `publication_authorized` remain false.
- [ ] `phase_19_forbidden` remains true.
- [ ] No real training/evaluation, publication analysis, native lifecycle claim, receipt edit, or `.git/gentle-ai` edit is present.

## Blocking failure conditions

Any missing or non-passing independent fallback review, unresolved OASIS semantics for an OASIS production path, provenance loss, target-label leakage, reused invalid split, three-class checkpoint load, legacy prediction-field acceptance, changed invariant, historical artifact mutation, or authorization flag change blocks acceptance. No implementation may be declared complete while a blocking condition remains.

## Evidence status

The current package contains specification text only. It does not contain implementation evidence, test output, real data, real split/hash evidence, review reports, publication metrics, or a binary freeze.
