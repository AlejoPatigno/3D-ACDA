# Phase 17 — Canonical Ablation Requirements

## 1. Outcome and gate

Phase 17 defines a scientifically auditable, compositional ablation contract. It does not run real data and does not promote a notebook helper to production by name alone. The implementation gate is:

> Only a candidate classified as `canonical_defined_not_executed` may become runnable after explicit maintainer approval of its exact one-intervention contract, complete fold/seed matrix, and output identity. `unsupported`, `helper_only`, `obsolete`, `equivalent_to_existing_method`, and `invalid_after_architecture_revision` candidates are not runnable ablation methods.

The current action produces specifications only. No production behavior, configuration, source/test/script file, real run, publication metric, or Phase 18 artifact is created.

## 2. Scientific questions

The approved questions for a future Phase 17 run are:

1. What is the effect of removing exactly one defined loss component from the canonical PADA-3DACB adaptation objective while preserving every other component and training identity?
2. Does replacing the retained attention aggregator with the exactly defined uniform mean aggregator change behavior, if and only if `mean_pool` is separately approved?
3. Is the historical `no_domain_adaptation` name a true Source-Only control, or only a loss-weight ablation that still forwards unlabeled target data?
4. Are results comparable across all predeclared transfer directions, folds, and seeds under one fixed epoch/checkpoint policy?
5. Do component diagnostics prove that only the intended raw and weighted term changed, without target-label leakage or target-guided selection?

These questions are diagnostic and comparative. They do not authorize claims of superiority, clinical effect, publication significance, or real-cohort performance.

## 3. Scope

In scope after explicit approval:

- exact candidates `no_proto`, `no_pl`, `no_cons`, `no_concept`, and `no_anat`;
- `mean_pool` only as a separately approved pooling intervention;
- an explicit equivalence/disposition record for `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, and `full`;
- source-only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16 behavior preservation;
- a single compositional registry, resolver, trainer integration, CLI boundary, and provenance-rich output contract;
- synthetic lifecycle, target-label firewall, resume, hash, and schema tests;
- future real-run authorization checks without executing the run in this phase.

## 4. Non-goals and protected behavior

The following are explicitly out of scope:

- real ADNI/OASIS data loading, training, or publication evaluation;
- target-supervised adaptation or target labels in any training loss;
- changing the PADA-3DACB model architecture, adding `ContextualROIEncoder`, adding `ctx_enc`, or adding a Full/Lite runtime switch;
- implementing `full` as a former contextual model;
- implementing `no_ctx_encoder` by patching a Full model;
- silently accepting long aliases;
- selecting `lambda_proto=0.2` or resolving `1.0` versus `0.2` by assumption;
- copying the historical selective-fold `availability` shortcut;
- early stopping, target-guided checkpoint selection, target-guided hyperparameter choice, epoch shortening, screening-only publication results, or inferred statistics;
- duplicate trainer implementations or new parallel training frameworks;
- modifying Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, or Phase 16 behavior;
- changing preprocessing, concept targets, Jacobian artifacts, split generation, or ROI ordering.

## 5. Candidate status and approval policy

| Candidate | Status | Runnable now? | Exact Phase 17 disposition |
|---|---|---:|---|
| `no_proto` | `canonical_defined_not_executed` | No | Requires explicit approval; set only `lambda_proto=0.0`. |
| `no_pl` | `canonical_defined_not_executed` | No | Requires explicit approval; set only `lambda_pl=0.0`. |
| `no_cons` | `canonical_defined_not_executed` | No | Requires explicit approval; set only `lambda_cons=0.0`. `no_head_consistency` is not an exact source symbol. |
| `no_concept` | `canonical_defined_not_executed` | No | Requires explicit approval; set only `lambda_cbm=0.0`. |
| `no_anat` | `canonical_defined_not_executed` | No | Requires explicit approval; set only `lambda_anat=0.0`. |
| `mean_pool` | `canonical_defined_not_executed` | No | Requires explicit approval; replace only the aggregator with the defined uniform mean. |
| `no_domain_adaptation` | `canonical_defined_not_executed` and semantically blocked | No | Cannot be called Source-Only until the loader and output contract prove no target adaptation consumption. |
| `no_ctx_encoder` | `equivalent_to_existing_method` and invalid as technique | No | Do not implement as an ablation or runtime switch. Current PADA-3DACB is already the no-context architecture. |
| `identity_ctx` | `helper_only` | No | Do not expose as a method. |
| `full` | `invalid_after_architecture_revision` | No | Do not implement; former contextual Full is not the current control. |
| `no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, `mean_pooling` | `unsupported` aliases | No | Reject unless an explicit exact mapping is approved; never create independent semantics. |

## 6. Exact one-intervention contracts

### 6.1 Common contract

Every runnable ablation record MUST contain:

- exact source name and immutable source provenance;
- one intervention kind: one loss coefficient override or one aggregator replacement;
- a complete inherited base configuration;
- an explicit preserved-component list;
- an explicit warm and full term table;
- a fixed direction, fold, and seed assignment;
- model/config/registry hashes;
- target adaptation/evaluation assignment hashes;
- checkpoint selection and resume identity;
- a diagnostic assertion that no unapproved term, architecture, loader, or artifact changed.

A registry resolver MUST reject unknown names, duplicate registry identities, multiple interventions, and overrides outside the approved whitelist.

### 6.2 Loss ablations

| Name | Only allowed change | Preserved components |
|---|---|---|
| `no_proto` | `lambda_proto = 0.0` | PADA-3DACB model; source losses; concept/anatomical losses; head consistency; pseudo-label loss; all data, optimizer, epochs, splits, and diagnostics. |
| `no_pl` | `lambda_pl = 0.0` | PADA-3DACB model; source losses; concept/anatomical losses; head consistency; prototype loss; all data, optimizer, epochs, splits, and diagnostics. |
| `no_cons` | `lambda_cons = 0.0` | PADA-3DACB model and every other loss term. Warm is numerically unchanged because `warm_lambda_cons=0.0`; full removes only the consistency contribution. |
| `no_concept` | `lambda_cbm = 0.0` | PADA-3DACB model, diagnosis heads, anatomical loss, head consistency, prototype, and pseudo-label terms. |
| `no_anat` | `lambda_anat = 0.0` | PADA-3DACB model, diagnosis heads, concept supervision, head consistency, prototype, and pseudo-label terms. |

No additional lambda, threshold, margin, smoothing, optimizer, schedule, batch size, epoch, architecture, or data field may be changed by these contracts.

### 6.3 Pooling ablation

`mean_pool` is one model intervention: replace the retained attention aggregator with the defined `MeanPoolAggregator` behavior `z = U.mean(dim=1)` and `alpha_k = 1/K` for every ROI. Encoder, tokenizer, token normalization/MLP/dropout, heads, losses, optimizer, data, epochs, splits, seeds, and output identities remain unchanged. It is not a Full/Lite variant and must not introduce `ctx_enc`.

## 7. Objective equations and invariants

The coefficients are inherited from the canonical primary contract: `lambda_z=1.0`, `lambda_c=1.0`, `lambda_cons=0.1`, `lambda_cbm=0.5`, `lambda_anat=0.2`, `lambda_proto=1.0`, `lambda_pl=0.1`, `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1`, `label_smoothing=0.1`, `warm_lambda_z=0.1`, `warm_lambda_c=1.0`, `warm_lambda_cbm=1.0`, `warm_lambda_anat=1.0`, and `warm_lambda_cons=0.0`. The later helper's `lambda_proto=0.2` remains unresolved and MUST fail resolution for publication-facing work.

Warm:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
        + warm_lambda_c    * lambda_c    * L_cls_c
        + warm_lambda_cbm  * lambda_cbm  * L_concept
        + warm_lambda_anat * lambda_anat * L_anat
        + warm_lambda_cons * lambda_cons * L_cons
```

Full:

```text
L_full = lambda_z    * L_cls_z
        + lambda_c    * L_cls_c
        + lambda_cons * L_cons
        + lambda_cbm  * L_concept
        + lambda_anat * L_anat
        + lambda_proto * L_proto
        + lambda_pl    * L_pl
```

Required invariants:

- warm never computes or weights prototype or pseudo-label adaptation; its logged `L_proto` and `L_pl` remain zero;
- full adaptation uses source labels only for source prototypes and target concept-head logits for pseudo-label decisions;
- all unmodified terms are numerically and structurally identical to the base configuration;
- diagnosis labels, target concept targets, target anatomical targets, and target Jacobian artifacts never enter adaptation;
- concept targets and Jacobian summaries are immutable precomputed source artifacts;
- class order is `[CN, MCI, AD]` with indices `{CN: 0, MCI: 1, AD: 2}`;
- all tensors are finite and dimension/device compatible;
- each runnable record has exactly one direction, one fold assignment, and one seed identity;
- no candidate may change model architecture except the explicitly approved `mean_pool` aggregator intervention;
- target metrics do not affect gradients, optimizer/scheduler state, checkpoint selection, hyperparameter selection, or epoch count.

## 8. Target-label firewall

A target-adaptation batch MUST contain exactly the four allowed fields `x`, `subject_id`, `subject_hash`, and `cohort`, and no other fields. Forbidden fields include `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, and other supervision/artifact fields. The implementation MUST reject forbidden or otherwise additional fields rather than dropping them silently.

`target_adaptation` and `target_evaluation` MUST be disjoint by assignment hash and subject identity. Target evaluation labels may be loaded only by a separate monitoring-only path. They MUST be labeled `MONITORING ONLY — NOT A TRAINING LOSS` and cannot affect loss, backward, optimizer, scheduler, checkpoint choice, epoch count, resume choice, or candidate selection.

## 9. Fixed epochs and checkpoint selection

The run configuration MUST declare warm and full epoch counts before training and train all declared epochs. Early stopping is forbidden. The source-validation macro-F1 is the sole best-checkpoint criterion. Training continues after a best checkpoint is saved. Target metrics are monitoring-only and cannot select a checkpoint.

The canonical Phase 17 specification does not invent new epoch counts. An implementation MUST receive them from the approved run configuration; if absent, conflicting, or modified by a candidate, it MUST fail before training. The notebook values `5` warm and `50` full are provenance of the primary call, not a new default.

## 10. Run, output, and resume contracts

A runnable invocation MUST:

1. resolve one exact candidate and one complete predeclared matrix;
2. freeze the resolved registry/config/model/split/loader identities;
3. write no real-data output before all preflight and firewall checks pass;
4. write atomic checkpoint, history, prediction, and equivalence-manifest artifacts under the candidate/direction/fold/seed directory contract;
5. include content hashes for configuration, model variant, registry, split assignments, target adaptation/evaluation assignments, precomputed artifacts, checkpoint, history, and predictions;
6. support interruption and resume only when all identity hashes and immutable contract fields match;
7. reject resume from a different candidate, alias, direction, fold, seed, matrix, architecture, loader partition, or coefficient resolution;
8. keep target monitoring namespaced separately from training losses.

The complete field-level schema is in `output_schema.md`. The output architecture and hash policy are in `design.md`.

## 11. Blocked and unsupported behavior

The resolver MUST fail closed with a structured reason for:

- a candidate without explicit approval;
- an unknown or unapproved alias;
- `lambda_proto=0.2` when the canonical primary value is required;
- `no_domain_adaptation` requested as Source-Only without a proven source-only loader path;
- `full`, `no_ctx_encoder`, or `identity_ctx` requested as a model variant;
- missing or partial direction/fold/seed matrix;
- target labels in adaptation batches;
- overlapping target adaptation/evaluation assignments;
- missing immutable concept/Jacobian artifacts;
- target-guided checkpoint or hyperparameter selection;
- changed inherited hyperparameters or multiple interventions;
- missing provenance, hashes, or resumable history;
- any attempt to run real data or publication evaluation from this specification-only action.

The error must identify the candidate, contract field, and remediation. It must not silently fall back to the base method or reinterpret a name.
