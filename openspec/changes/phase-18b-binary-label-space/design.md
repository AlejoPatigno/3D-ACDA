# Phase 18B Binary Label Space Design

**Change status:** `planning`

This artifact is planning-only. It does not claim production implementation, real data execution, tests, independent review, gate passage, publication analysis, native lifecycle validation, or receipt changes.

## Normative source

The normative specification is:

`openspec/changes/phase-18b-binary-label-space/specs/label-space/spec.md`

The package companion documents are under `specs/phase_18b_binary_label_space/`.

## Decision summary

- Primary task: `CN` versus `Impaired`.
- Fixed class order: `CN=0`, `Impaired=1`; never derive order alphabetically.
- Canonical ADNI mapping: `CN→CN`, `MCI→Impaired`, `AD→Impaired`.
- Missing, unknown, malformed, unsupported, and out-of-domain ADNI labels reject; duplicate subjects and conflicting diagnoses are excluded pending explicit policy.
- Original diagnosis and mapping provenance remain mandatory.
- OASIS semantics are blocked because no approved canonical manifest or metadata-generation provenance is available. Ambiguous, unknown, missing, malformed, conflicting, and out-of-domain OASIS values reject or exclude; no OASIS MCI is invented.
- Split disposition: `REGENERATE_BINARY_SPLITS_REQUIRED` unless exact binary validity is proven later.
- Binary classifier heads emit two raw logits shaped `(B,2)` with integer targets `{0,1}`, consumed by PyTorch-style `CrossEntropyLoss`; concept outputs remain `(B,K)`. This is not `BCEWithLogitsLoss`, sigmoid, or one-logit BCE.
- CDAN uses runtime `z_dim*n_classes`, with required `(128,2)->256` and distinct configuration plus gradient-to-`z`/`p` checks.
- Prototype/pseudo paths use two raw logits shaped `(B,2)` and integer targets `{0,1}` with PyTorch-style `CrossEntropyLoss`, cover absent classes, return zero loss for an empty accepted set, and receive no target diagnosis; `BCEWithLogitsLoss`, sigmoid, and one-logit BCE are prohibited.
- Three-class checkpoints fail closed; partial loading is prohibited.
- Predictions use `prob_cn` and `prob_impaired`, reject active `prob_mci`/`prob_ad`, use shared float64/float32 tolerances, and select lower-index CN on ties.
- Undefined metrics are `null` plus reason, never coerced.
- Experiment, split, model/checkpoint, training metadata, evaluation result, and freeze identities reject historical three-class collisions.

## Boundaries and sequencing

Before both gates pass, only documentation, specification maintenance, and synthetic contract-test planning are allowed; that work is not implementation. Production implementation is permitted only after verified OASIS semantics approval and both fresh independent fallback reviews pass the complete checklist.

Kimi and Gemini CLI are unavailable. `fallback-review-1` and `fallback-review-2` are recorded fresh independent substitutions, non-authorizing until each passes the complete checklist, and currently pending. No review pass is claimed.

Real training/evaluation, publication analysis, real OASIS mapping or splits, native lifecycle operations, receipt edits, and Phase 19 execution remain forbidden.

## Artifact and historical boundary

Binary identities, matrices, split manifests, checkpoint metadata, evaluation results, and freeze artifacts use a binary-scoped identity. Historical Phase 18 three-class artifacts remain unchanged and are marked only in new Phase 18B artifacts with `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`.

Protected state remains:

```yaml
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

Receipt `review-1d63ad8511d6bbf5` remains untouched.

## Dependencies and gates

1. Maintain the contract package and normative nested specification.
2. Obtain both substituted independent checklist passes; `fallback-review-1` and `fallback-review-2` remain pending and non-authorizing until then.
3. Verify and approve the OASIS canonical manifest and metadata-generation provenance; status remains blocked.
4. Only after OASIS approval and both fallback passes may production implementation be considered, subject to the remaining safety boundaries. Phase 19 interface design may be documented only; Phase 19 execution remains forbidden.
