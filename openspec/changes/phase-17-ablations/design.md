# Phase 17 — Compositional Synthetic Ablation Design

## Decision first

Use one thin composition layer around the current PADA-3DACB architecture and one existing fixed-epoch trainer. A registry and pure resolver freeze exact candidate identity, approval, intervention, matrix, architecture, target firewall, and hashes before the trainer receives data. No notebook runner is copied, no duplicate trainer is created, and the former contextual model is not revived.

This design is for synthetic/test implementation only. It does not authorize a real run or publication evaluation.

## Architecture

```text
exact candidate request + approval + complete matrix
                         |
                         v
                  immutable registry
                         |
                         v
                     resolver
        (disposition, one intervention, firewall, hashes)
                         |
                         v
        current PADA-3DACB model + one composition point
             |                               |
             +------------> one existing trainer
                                             |
                                             v
              atomic checkpoint/history/prediction outputs
                  + config/reproducibility/equivalence index
```

The single production boundary is:

```text
Encoder3D -> ROITokenizer -> token normalization/MLP/dropout
          -> AttentionAggregator -> ClassificationHead + ConceptBottleneck
```

Loss candidates preserve this model and replace one named coefficient. `mean_pool` is represented only as:

```text
PADA-3DACB + MeanPoolAggregator
```

where `z = U.mean(dim=1)` and `alpha_k = 1/K`. It is not `Full`, `Lite`, `Contextual`, `identity_ctx`, or a patched checkpoint. No resolved production configuration may contain `ContextualROIEncoder` or `ctx_enc`.

## Registry and resolver

The registry is the sole identity source. Each entry contains exact source ID, classification, explicit approval, provenance, one intervention, preserved components, warm/full term activity, aliases, disposition, and blocked reason. The six approved synthetic entries are `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, and `mean_pool`, with interventions exactly preserved from the audited source.

The registry also retains blocked records for `no_domain_adaptation`, `full`, `no_ctx_encoder`, `identity_ctx`, unsupported aliases, and unresolved configurations. A rejected request remains visible in the equivalence manifest; it is never silently downgraded to the base method.

`resolve_ablation` is pure preflight. It normalizes only exact IDs and explicitly approved one-to-one aliases, requires candidate approval, validates one intervention, copies the canonical primary coefficients, rejects the unresolved `lambda_proto=0.2`/`1.0` choice, enforces the current architecture, validates the complete direction/fold/seed matrix and disjoint target assignments, and computes all input identity hashes. Resolution fails before data loading for unknown, unapproved, contextual, Source-Only-unproven, alias, incomplete, target-supervised, hash, or real-run requests.

## Composition and diagnostics

A resolved loss candidate clones the inherited coefficient map and sets exactly one approved coefficient to zero. `no_cons` therefore has no effective warm-stage change because `warm_lambda_cons = 0.0`; its full-stage consistency term alone is disabled. `no_concept` and `no_anat` preserve the concept head and immutable source artifacts even when their corresponding weighted terms are disabled. `mean_pool` replaces only the retained aggregator.

The composition layer exposes active, raw, and weighted component diagnostics. Raw values may remain observable when a candidate disables weighting, but the weighted component and active flag must identify the intervention. Warm prototype and pseudo-label terms remain absent and logged zero. The diagnostics make it possible to assert that no other loss, architecture, data, optimizer, schedule, or artifact changed.

## Trainer integration

The existing trainer remains the sole owner of:

- warm/full sequencing;
- optimizer and scheduler state;
- source-validation macro-F1 checkpoint selection;
- fixed epoch completion;
- target monitoring;
- checkpoint/resume capture;
- history flushing.

The ablation layer supplies resolved model, loss, configuration, diagnostics, and provenance. It does not add a second loop or duplicate method-specific behavior. Target adaptation is passed only where the existing UDA contract requires it and must contain exactly the allowed keys `x`, `subject_id`, `subject_hash`, and `cohort`. A future Source-Only candidate must use the protected Source-Only path or an explicitly proven no-target path; zeroing UDA weights is not sufficient.

## Target firewall

The resolver and trainer validate target adaptation batches before loss computation. Any `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, or other supervision/artifact field is rejected instead of dropped. Target adaptation and target evaluation have disjoint subject identities and separate assignment hashes. Target evaluation remains disjoint and monitoring-only; its labels exist only in a namespaced monitoring path marked:

```text
MONITORING ONLY — NOT A TRAINING LOSS
```

Monitoring cannot affect gradients, optimizer/scheduler state, checkpoint choice, hyperparameters, epoch count, resume choice, or candidate selection.

## Identity and output design

Hashes use SHA-256 over canonical UTF-8 JSON bytes with sorted object keys, stable list ordering, no timestamps in hashed payloads, and a declared canonicalization version. The resolver freezes:

- `registry_hash`;
- `candidate_hash`;
- `resolved_config_hash`;
- `model_variant_hash`;
- source split, target adaptation, and target evaluation assignment hashes;
- immutable precomputed-artifact hash.

After writing, checkpoint, history, prediction, and equivalence-manifest hashes are recomputed and indexed. A resume is valid only when every candidate, approval, configuration, model, registry, direction, fold, seed, matrix, assignment, artifact, and hash identity matches exactly.

The output directory is:

```text
<output_root>/<candidate_id>/<source>_to_<target>/seed_<SEED>/fold_<NN>/
```

It contains:

```text
checkpoint_last.pt
checkpoint_best_source_f1.pt
checkpoint_epoch_<NNN>.pt
training_history.json
predictions.jsonl
equivalence_manifest.json
config_resolved.json
reproducibility_metadata.json
artifact_index.json
```

Writes are atomic and hash-verified. Blocked requests create only a structured preflight result outside a run directory. Synthetic and blocked artifacts carry `real_data_run: false` and `publication_metrics_present: false`.

## Epoch and checkpoint policy

Warm and full epoch counts are explicit approved inputs; notebook values `5/50` are provenance, not silently promoted defaults. Early stopping is unavailable. The trainer writes a recoverable last checkpoint each epoch and updates the best checkpoint only on improved source-validation macro-F1, then continues through all configured epochs. Target metrics are monitoring-only.

Checkpoints capture applicable model, optimizer, scheduler, and scaler state; stage, epoch/global step, best source value, history append position, RNG/loader-generator state, identity hashes, and `contains_mri_data: false`. Target checkpoint-selection state is absent or empty.

## Tradeoffs and rejected alternatives

| Decision | Tradeoff | Rationale |
|---|---|---|
| One composition layer around one trainer | Less local freedom than copying notebook runners | Prevents shadowed definitions, behavior drift, and duplicate lifecycle ownership. |
| Exact IDs and explicit aliases only | Longer names may be rejected | Scientific identity is safer than name-based convenience; rejected aliases remain auditable. |
| Current PADA-3DACB as the only base model | Historical contextual comparisons are unavailable | The architecture revision removed the contextual path; recreating it would be a new, unsupported method. |
| `mean_pool` as an aggregator composition | Requires a distinct model hash | It isolates the architectural intervention without creating a Full/Lite switch or duplicate model family. |
| Fixed epochs and source-only checkpoint selection | No early stopping or target-optimized screening | Preserves comparability and prevents target leakage. |
| Complete direction/fold/seed matrix | More setup before a smoke run | Rejects the historical selective-fold shortcut and makes comparisons auditable. |
| Atomic, hash-bound outputs | More metadata and validation work | Makes interruption, resume, partial writes, and identity drift fail closed. |

## Protected dispositions

- `no_domain_adaptation` remains `BLOCKED_NOT_PROVEN` as Source-Only until loader, forward, gradient, method identity, output, and synthetic regression proof exists.
- `full` is `INVALID_AFTER_ARCHITECTURE_REVISION`.
- `no_ctx_encoder` is equivalent in resulting no-context behavior but invalid as a patching technique.
- `identity_ctx` is `HELPER_ONLY`.
- `no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, and `mean_pooling` remain unsupported aliases without explicit mapping.
- `lambda_proto=0.2` versus `lambda_proto=1.0` remains unresolved.
- CFS, ACS, PCS, and QIS remain blocked without authoritative equations.

## Boundary and rollback

Preflight runs before data loading and before run-directory creation. Any failed firewall, approval, matrix, hash, schema, or authorization check stops without mutating an existing identity. An interrupted synthetic run may be resumed only after exact identity validation; otherwise it remains incomplete and is not rewritten as evidence. No command in this design loads real ADNI/OASIS data, emits publication metrics, or begins Phase 18.
