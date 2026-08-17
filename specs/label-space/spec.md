# Label-Space Specification: Phase 18B Binary Publication Task

**Specification status:** Planning; not approved for implementation.

## Authorization and review gate

This package permits only documentation/specification maintenance and synthetic contract-test planning before the gates pass. Production implementation is permitted only after OASIS semantics are verified and approved **and** both fresh independent fallback reviews pass the complete checklist: `fallback-review-1` (substituted for unavailable Kimi) and `fallback-review-2` (substituted for unavailable Gemini CLI). Both statuses remain pending and non-authorizing; no review or OASIS pass is claimed.

## Contract

The publication task is binary `CN` versus `Impaired` with fixed IDs:

```yaml
task: CN_vs_Impaired
class_order: [CN, Impaired]
class_ids:
  CN: 0
  Impaired: 1
```

The order is part of the contract and is never inferred alphabetically or from a dataset.

## ADNI mapping

| Original diagnosis | Task label | ID |
|---|---|---:|
| `CN` | `CN` | 0 |
| `MCI` | `Impaired` | 1 |
| `AD` | `Impaired` | 1 |

This is a publication-task grouping. It does not state that MCI and AD are diagnostically equivalent. Included records retain original diagnosis and mapping provenance.

## Record contract

A derived record must preserve, at minimum:

```yaml
original_label_name: <source diagnosis>
binary_label_name: CN | Impaired
binary_label: 0 | 1
cohort: <source cohort>
subject_id: <auditable subject identity>
mapping_contract: <version/provenance>
```

Missing, malformed, unsupported, ambiguous, or conflicting source labels are excluded or rejected by an explicit policy. Already-derived labels without original provenance fail closed.

## OASIS gate

OASIS production semantics are **BLOCKED**. Repository evidence records:

- `configs/data/oasis.yaml` has `root: null` and `metadata_csv: null`;
- no approved real OASIS manifest is available in this package;
- the legacy loader requires an ID/Subject ID-compatible field and `CDR`, skips missing CDR, maps `CDR == 0` to `CN`, and maps all other numeric CDR values to historical `AD`.

The legacy behavior is evidence only, not final semantics. Before OASIS can participate in an approved binary cohort, maintainers must approve the canonical manifest and metadata-generation provenance, source fields and value domain, missing-value policy, duplicate/longitudinal policy, and unambiguous mapping. No OASIS MCI category may be invented; ambiguous or unknown records are excluded.

## Splits and artifact identity

The split disposition is `REGENERATE_BINARY_SPLITS_REQUIRED`. Reuse requires exact proof of binary cohort validity, stratification, leakage protection, target partition separation, deterministic parameters, and identity compatibility. No real split manifest, hash, class count, or binary freeze is claimed.

Binary identities must be distinguishable from historical Phase 18 three-class identities. New Phase 18B artifacts use the additive conceptual marker:

`SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`

Historical three-class files are preserved and are not rewritten by this specification.

## Model contract

- Task classifier emits two raw logits shaped `(B,2)` and integer class targets are `{0,1}`, consumed by PyTorch-style `CrossEntropyLoss`.
- This is **not** `BCEWithLogitsLoss`, does not apply sigmoid, and is not one-logit BCE.
- Concept outputs/artifacts: `(B, K)`, unchanged.
- CDAN conditioning width: `z_dim * n_classes`; at `z_dim=128`, `128*2=256`.
- CORAL/MMD: unchanged mathematics.
- Target adaptation: label-free; target adaptation and evaluation partitions remain disjoint.
- Three-class checkpoint: fail closed; no partial loading or classifier-key omission.

## Prediction and evaluation

Predictions expose `prob_cn` and `prob_impaired` in the fixed class order. Evaluation uses a 2x2 confusion matrix with true labels as rows, predicted labels as columns, and `Impaired` as primary positive. Required metrics are accuracy, precision, recall/sensitivity, F1, and AUC-ROC. Source-validation macro-F1 remains the only best-checkpoint selection criterion. Concept targets and concept macro-F1 remain unchanged.

CN-versus-AD sensitivity is specification-only: it filters original CN and original AD provenance, excludes MCI and unresolved records, defines AD as positive, and produces no result in this phase.

## Authorization state

```yaml
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

Both fresh independent fallback reviews—`fallback-review-1` substituted for unavailable Kimi and `fallback-review-2` substituted for unavailable Gemini CLI—must pass the complete checklist before production implementation. Both remain pending and non-authorizing. The OASIS gate must also resolve before production OASIS mapping. Neither gate has passed. Real training/evaluation, publication analysis/results, Phase 19 execution, native lifecycle claims, receipt edits, and historical artifact edits remain outside scope.
