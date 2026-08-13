# Phase 17 — Compositional Ablation Design

## 1. Design decision

Implement one thin ablation composition layer around the existing training architecture. The layer resolves an approved immutable specification into a base method, one exact intervention, and provenance metadata. It must not copy the notebook's shadowed runners, create a second trainer, revive the former contextual model, or add a Full/contextual runtime switch.

The architecture boundary is the current explicit PADA-3DACB model: `Encoder3D -> ROITokenizer -> token normalization/MLP/dropout -> AttentionAggregator -> ClassificationHead + ConceptBottleneck`. `full`, `ctx_enc`, `ContextualROIEncoder`, `identity_ctx`, and patched Full construction are historical evidence only. `mean_pool`, if approved, is a single aggregator replacement inside this boundary, not a model variant.

This document specifies architecture and contracts; it does not authorize implementation or a real run.

## 2. Component map

```text
approved registry entry
        |
        v
candidate resolver ----> exact contract + hashes + blocked reason
        |
        v
base PADA-3DACB builder -- optional one intervention --> one model/loss composition
        |                                                       |
        +--------------------> one existing trainer <-----------+
                                      |
                                      v
                                  CLI runner
                                      |
             checkpoint / history / prediction / equivalence manifest
```

### 2.1 Registry

The registry is the sole source of runnable ablation identities. Each entry contains:

- `id`: exact source name only;
- `classification`: inventory classification;
- `approval`: explicit approval record required for `canonical_defined_not_executed`;
- `provenance`: notebook path, cell, and source lines;
- `intervention`: exactly one `loss_override` or one `aggregator_replacement`;
- `preserved_components`: explicit inherited components;
- `warm_terms` and `full_terms`: resolved term activity;
- `aliases`: empty by default; any accepted alias must point to this exact `id` and never create a second entry;
- `blocked_reason`: required for all non-runnable entries.

Registry entries for `full`, `no_ctx_encoder`, `identity_ctx`, `no_domain_adaptation`, and unsupported aliases remain non-runnable in the initial state. The registry must retain their disposition so a CLI rejection is explainable.

### 2.2 Resolver

`resolve_ablation(request, base_configuration, approval, matrix)` performs pure validation and returns either a resolved immutable contract or a structured blocked error. It must:

1. normalize only exact IDs and explicitly approved aliases;
2. reject unknown, ambiguous, long, or case-altered names;
3. require approval for every `canonical_defined_not_executed` entry;
4. verify one intervention only;
5. copy the canonical primary coefficients and reject unapproved overrides;
6. reject the unresolved `lambda_proto=0.2` configuration where `lambda_proto=1.0` is required;
7. enforce the explicit PADA-3DACB model boundary;
8. reject `full`, `ctx_enc`, `identity_ctx`, and any contextual switch;
9. reject `no_domain_adaptation` unless its source-only loader proof is present;
10. validate the complete direction/fold/seed matrix and disjoint target assignments;
11. compute the registry, candidate, resolved-config, model-variant, and assignment hashes;
12. return the exact output identity used by the trainer and CLI.

The resolver is not allowed to infer semantics from descriptions, use notebook defaults as new defaults, or silently downgrade a blocked candidate to base PADA-3DACB.

### 2.3 Intervention composition

A resolved contract is applied to one base method in one composition point:

- loss candidate: clone the resolved coefficient map and replace exactly one named coefficient with zero;
- `mean_pool`: construct the current PADA-3DACB model and replace only its retained aggregator with the defined uniform aggregator;
- no other model, loss, loader, optimizer, schedule, artifact, or metric behavior changes.

Composition must be explicit and inspectable. It must expose active/raw/weighted component diagnostics so a test can prove that the intervention changed only its target term. The system must not deep-copy or patch a former Full model.

### 2.4 Trainer integration — no duplicate trainer

Use the existing fixed-epoch trainer abstraction and its existing method-specific adaptation interfaces. The ablation layer supplies resolved model/loss/configuration objects and provenance; it does not add a parallel trainer loop. There must be exactly one owner for:

- warm/full epoch sequencing;
- optimizer and scheduler state;
- source-validation checkpoint selection;
- target monitoring;
- checkpoint/resume state capture;
- history flushing.

The trainer receives `target_adaptation_loader` only for methods that require it. A future proven Source-Only control must use the existing source-only trainer path or an explicit no-target adaptation path, not a target loader with zeroed adaptation weights. The historical `no_domain_adaptation` helper is therefore blocked until this boundary is proven.

### 2.5 Target-label firewall

The target-adaptation loader boundary MUST accept batches containing exactly the four allowed fields `x`, `subject_id`, `subject_hash`, and `cohort`, and no others. Forbidden fields include `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, and other supervision/artifact fields. The loader or resolver MUST reject forbidden or additional fields before loss computation rather than dropping them silently.

`target_adaptation` and `target_evaluation` MUST remain disjoint by assignment hash and subject identity. Target evaluation is a separate monitoring-only path; its labels and metrics MUST be labeled `MONITORING ONLY — NOT A TRAINING LOSS` and MUST NOT affect loss, backward, optimizer, scheduler, checkpoint choice, epoch count, resume choice, or candidate selection.

### 2.6 CLI

The CLI is a preflight and lifecycle adapter, not a scientific policy engine. It accepts:

- exact candidate ID;
- approved run configuration reference;
- fixed direction/fold/seed matrix reference;
- output root;
- optional resume checkpoint;
- explicit synthetic-smoke mode for lifecycle tests.

The CLI must resolve before data loading/training and print or persist a structured blocked result when resolution fails. It must require an explicit real-run authorization boundary outside this specification. No default command may run ADNI/OASIS or publication evaluation.

## 3. Explicit model-variant boundary

There is one production model variant: PADA-3DACB. Its retained components are `Encoder3D`, `ROITokenizer`, token normalization/MLP/dropout, `AttentionAggregator`, `ClassificationHead`, and `ConceptBottleneck`.

`mean_pool` is represented as:

```text
PADA-3DACB + aggregator = MeanPoolAggregator
```

It is not represented as `Lite`, `Full`, `Contextual`, `identity_ctx`, or a patched checkpoint. No `ctx_enc` field may appear in a resolved production model configuration. A model hash must change for `mean_pool` and remain identical between loss-only ablations and the base PADA-3DACB model.

## 4. Equivalence and disposition handling

The equivalence resolver records a three-way disposition:

- `equivalent_to_existing_method`: behavior is already represented by a protected method and must not receive a second runnable identity;
- `invalid_after_architecture_revision`: historical behavior depends on removed architecture and is rejected;
- `blocked_not_proven`: name or intervention is defined, but the requested scientific interpretation is not established.

`no_ctx_encoder` is equivalent in resulting no-context behavior to current PADA-3DACB but invalid as an implementation technique. `full` is invalid after the architecture revision. `no_domain_adaptation` is blocked as Source-Only because the historical runner still constructs/forwards target adaptation data. The exact evidence and rejection messages belong in `equivalence_map.md`.

No alias is silently accepted. An accepted alias is recorded as a one-to-one mapping with exact provenance and the canonical ID remains the output identity.

## 5. Hash and identity design

All hashes are SHA-256 over canonical UTF-8 JSON bytes with sorted object keys, stable list ordering, and no timestamps. The output must record the algorithm and canonicalization version.

Required identities:

| Hash | Input |
|---|---|
| `registry_hash` | Complete registry entries and dispositions used by the resolver. |
| `candidate_hash` | Exact ID, classification, provenance, intervention, preserved terms, and approval record. |
| `resolved_config_hash` | All inherited and overridden training/loss fields after resolution. |
| `model_variant_hash` | Explicit model variant and architecture component manifest. |
| `source_split_assignment_hash` | Ordered source subject/fold assignment manifest. |
| `target_adaptation_assignment_hash` | Ordered unlabeled target adaptation subject/fold assignment manifest. |
| `target_evaluation_assignment_hash` | Ordered labeled monitoring-only target evaluation assignment manifest. |
| `precomputed_artifacts_hash` | Immutable concept/Jacobian/artifact index identities used by the run. |
| `checkpoint_hash` | Final checkpoint bytes. |
| `history_hash` | Canonical history JSON/CSV content after flush. |
| `prediction_hash` | Canonical prediction artifact bytes. |
| `equivalence_manifest_hash` | Canonical equivalence/disposition manifest. |

A resume is valid only when all input identity hashes match the checkpoint and the candidate is still approved. Output hashes are recomputed after write and recorded in the manifest; a mismatch is a hard failure.

## 6. Directory contract

A future runnable output uses this shape:

```text
<output_root>/
  <candidate_id>/
    <source>_to_<target>/
      seed_<SEED>/
        fold_<NN>/
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

The directory identity is exact candidate ID, direction, fold, and seed. It must not use a requested alias, `full`, or `no_domain_adaptation` as a substitute for an unresolved disposition. Files are described in `output_schema.md`.

## 7. History and checkpoint policy

History rows record stage (`warm` or `full`), epoch, global step, learning rate, total loss, every raw and weighted component, active flags, diagnostics, source metrics, target monitoring metrics, and timing/runtime data. Target monitoring is namespaced and labeled; it is never merged into training loss fields.

The trainer writes `checkpoint_last.pt` each recoverable epoch and updates `checkpoint_best_source_f1.pt` only on improved source-validation macro-F1. It continues for all configured epochs. Checkpoints contain model, optimizer, scheduler if present, AMP scaler if present, epoch/global step, best source macro-F1, RNG and loader-generator states, resolved config/hash, assignment hashes, artifact hashes, and history append position. They contain no MRI data and no target checkpoint-selection state.

## 8. Protected-method integration

The ablation resolver must use existing method names and adapters for Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16. It must not change their registry entries, loss equations, trainer semantics, output schemas, or checkpoint behavior. Any shared helper change must be regression-tested against those methods before Phase 17 implementation can be approved.

## 9. Failure modes

All failures are structured and fail closed:

- `unknown_candidate`;
- `alias_not_approved`;
- `candidate_not_approved`;
- `unsupported_candidate`;
- `architecture_disposition_blocked`;
- `source_only_not_proven`;
- `multiple_interventions`;
- `unapproved_override`;
- `unresolved_coefficient`;
- `incomplete_matrix`;
- `target_label_firewall_violation`;
- `overlapping_target_assignments`;
- `hash_mismatch`;
- `resume_identity_mismatch`;
- `real_run_not_authorized`.

No failure may silently run the base method, select another candidate, drop target fields, shorten the matrix, or reinterpret an alias.
