# Phase 17 Ablation Contracts

This is a delta specification for the Phase 17 synthetic-only implementation boundary. It adds no real-data or publication behavior.

## ADDED Requirements

### Requirement: The registry MUST preserve exact candidate identity and approval boundaries

The registry MUST be the sole source of ablation identity. It MUST preserve exact IDs, notebook provenance, classification, disposition, approval, intervention, preserved components, warm/full term activity, aliases, and blocked reasons. It MUST expose the six explicitly approved synthetic candidates and retain all excluded candidates as fail-closed records. It MUST not infer semantics from descriptions, spelling variants, comments, or historical helper defaults.

Approved exact IDs and interventions are:

| ID | Exact intervention |
|---|---|
| `no_proto` | `lambda_proto = 0.0` |
| `no_pl` | `lambda_pl = 0.0` |
| `no_cons` | `lambda_cons = 0.0` |
| `no_concept` | `lambda_cbm = 0.0` |
| `no_anat` | `lambda_anat = 0.0` |
| `mean_pool` | Replace attention aggregation with exact uniform mean: `z = U.mean(dim=1)`, `alpha = 1/K`. |

#### Scenario: Resolve an approved exact loss candidate

- **Given** a request for exact ID `no_proto`, an explicit approval record, canonical primary configuration, and a complete synthetic matrix
- **When** the registry resolver validates the request
- **Then** it resolves `no_proto` with only `lambda_proto = 0.0`, preserves every other inherited field, and emits the exact candidate identity and provenance

#### Scenario: Reject an unapproved or unsupported name

- **Given** a request for `no_prototype`, `no_head_consistency`, `source_only`, or another unknown/alias spelling without explicit one-to-one approval
- **When** the resolver validates the request
- **Then** it fails closed with a structured alias or unknown-candidate reason and does not create a second registry identity

### Requirement: Each runnable candidate MUST apply exactly one intervention

A runnable loss candidate MUST change exactly one whitelisted coefficient and a pooling candidate MUST change only the retained aggregator. All inherited coefficients, thresholds, margins, smoothing, optimizer, schedule, epochs, data, splits, seeds, immutable concept/Jacobian artifacts, diagnostics, and output identity rules MUST remain unchanged. The canonical primary coefficients MUST be used, including `lambda_proto = 1.0`; the later helper value `lambda_proto = 0.2` MUST remain unresolved and MUST NOT be selected by assumption.

The warm objective MUST be:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
        + warm_lambda_c    * lambda_c    * L_cls_c
        + warm_lambda_cbm  * lambda_cbm  * L_concept
        + warm_lambda_anat * lambda_anat * L_anat
        + warm_lambda_cons * lambda_cons * L_cons
```

The full objective MUST be:

```text
L_full = lambda_z     * L_cls_z
        + lambda_c     * L_cls_c
        + lambda_cons  * L_cons
        + lambda_cbm   * L_concept
        + lambda_anat  * L_anat
        + lambda_proto * L_proto
        + lambda_pl    * L_pl
```

Warm `L_proto` and `L_pl` MUST be absent from computation and logged as zero. Full prototype and pseudo-label probabilities MUST use target concept-head logits, never target diagnosis labels.

#### Scenario: Reject multiple or unapproved interventions

- **Given** a request that changes two coefficients, changes a non-whitelisted coefficient, or changes an inherited epoch/split/optimizer field
- **When** the resolver composes the candidate
- **Then** it fails with `multiple_interventions` or `unapproved_override` before data loading or training

#### Scenario: Preserve warm and full term activity

- **Given** each of the five approved loss candidates
- **When** synthetic composition computes warm and full diagnostics
- **Then** warm adaptation components remain inactive and zero, and full diagnostics show only the candidate's named weighted term disabled while all other terms retain their base activity and values

### Requirement: The current PADA-3DACB architecture MUST be the only model boundary

The implementation MUST reuse the explicit `Encoder3D -> ROITokenizer -> token normalization/MLP/dropout -> AttentionAggregator -> ClassificationHead + ConceptBottleneck` architecture and one existing trainer integration. It MUST NOT introduce `ContextualROIEncoder`, `ctx_enc`, a Full/Lite switch, identity-patched Full construction, or a duplicate trainer. `mean_pool` MUST be represented as `PADA-3DACB + MeanPoolAggregator`, with no contextual field in the resolved production model configuration. Its model hash MUST differ from loss-only/base PADA-3DACB hashes; loss-only candidates MUST preserve the base model hash.

#### Scenario: Resolve mean pooling as one explicit aggregator intervention

- **Given** an approved exact request for `mean_pool`
- **When** the model composition is resolved
- **Then** only the retained aggregator is replaced with `z = U.mean(dim=1)` and uniform `alpha = 1/K`, all other model/loss/training components are preserved, and a distinct model-variant hash is emitted

#### Scenario: Reject former contextual variants

- **Given** a request for `full`, `no_ctx_encoder`, `identity_ctx`, `ctx_enc`, or a contextual runtime switch
- **When** resolution is attempted
- **Then** it fails closed with the recorded invalid, equivalent, or helper-only disposition and does not instantiate or patch a contextual model

### Requirement: Target adaptation MUST be protected by a label firewall

A target adaptation batch MUST contain exactly the allowed target-adaptation keys: `x`, `subject_id`, `subject_hash`, and `cohort`. The resolver/trainer MUST reject `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, and other supervision/artifact fields before loss computation rather than dropping them silently. Target adaptation and target evaluation assignments MUST be disjoint by subject identity and separate assignment hashes. Target evaluation remains disjoint and monitoring-only; its labels MAY be loaded only by a separate path labeled `MONITORING ONLY — NOT A TRAINING LOSS`.

Target monitoring MUST NOT affect gradients, optimizer or scheduler state, checkpoint selection, hyperparameter selection, epoch count, resume choice, candidate selection, or training loss fields.

#### Scenario: Accept unlabeled target adaptation

- **Given** a target adaptation batch with exactly the allowed keys `x`, `subject_id`, `subject_hash`, and `cohort`, plus a disjoint monitoring assignment
- **When** it enters the adaptation trainer
- **Then** it is accepted for unlabeled adaptation and cannot expose target diagnosis supervision to the loss

#### Scenario: Reject target supervision before loss computation

- **Given** a target adaptation batch containing `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, or another forbidden supervision/artifact field
- **When** firewall validation runs
- **Then** it rejects the batch with `target_label_firewall_violation` before forward/loss/gradient computation

#### Scenario: Keep target monitoring observational

- **Given** labeled target evaluation data in a disjoint monitoring path
- **When** target metrics are recorded
- **Then** metrics are namespaced with the exact monitoring-only label and cannot change checkpoint choice, optimizer state, gradients, epoch count, or resume identity

### Requirement: Every run MUST freeze complete assignments and hash identities

A run MUST declare a complete direction/fold/seed matrix before training. The historical selective-fold `availability` shortcut MUST be rejected. Canonical identities MUST use SHA-256 over canonical UTF-8 JSON with sorted keys, stable list ordering, no timestamps in hashed payloads, and a declared canonicalization version. Required identities include registry, candidate, resolved configuration, model variant, source split, target adaptation assignment, target evaluation assignment, immutable precomputed artifacts, checkpoint, history, prediction, and equivalence manifest hashes.

A resume MUST succeed only when candidate, approval, configuration, model variant, registry, direction, fold, seed, complete matrix, split assignments, target assignments, artifact identities, hash algorithm, and all corresponding hashes match exactly. Partial, mismatched, or stale artifacts MUST fail closed without overwriting another identity.

#### Scenario: Reject an incomplete matrix

- **Given** a request with a missing direction, fold, or seed from the predeclared matrix, or one using selective availability
- **When** preflight validation runs
- **Then** it fails with `incomplete_matrix` before data loading and creates no training artifact

#### Scenario: Resume the same synthetic identity

- **Given** an interrupted synthetic run and a checkpoint whose full identity envelope matches the resolved request
- **When** resume validation runs
- **Then** it resumes from the recorded history position without duplicate rows or identity changes

#### Scenario: Reject a mismatched resume

- **Given** a checkpoint from another candidate, alias, direction, fold, seed, assignment, coefficient resolution, model variant, or artifact set
- **When** resume validation runs
- **Then** it fails with `resume_identity_mismatch` or `hash_mismatch` and does not overwrite the existing run

### Requirement: Checkpointing MUST use fixed epochs and source-only selection

Warm and full epoch counts MUST be explicit approved inputs. Every declared epoch MUST run; early stopping MUST be unavailable. `checkpoint_best_source_f1.pt` MUST update only when source-validation macro-F1 improves. Training MUST continue after a best save. Target metrics MUST NOT select checkpoints or hyperparameters. Checkpoints MUST capture applicable model/optimizer/scheduler/scaler state, epoch/global step, stage, best source value, history position, RNG/loader states, identity hashes, and `contains_mri_data: false`.

#### Scenario: Complete the declared lifecycle

- **Given** explicit warm/full epoch inputs and a synthetic fixture
- **When** the trainer runs
- **Then** it executes every warm and full epoch, writes recoverable last checkpoints, and continues through the configured final epoch after any source-validation best save

#### Scenario: Ignore target metrics for selection

- **Given** target monitoring metrics that improve or worsen independently of source-validation macro-F1
- **When** checkpoint selection executes
- **Then** only source-validation macro-F1 can update the best checkpoint and no target metric enters optimizer, scheduler, hyperparameter, or epoch decisions

### Requirement: Outputs MUST be atomic, provenance-rich, and schema-valid

A runnable output MUST use:

```text
<output_root>/<candidate_id>/<source>_to_<target>/seed_<SEED>/fold_<NN>/
```

The directory MUST contain checkpoint, history, prediction, resolved configuration, reproducibility metadata, artifact index, and equivalence manifest artifacts. Every artifact MUST carry phase/schema identity and candidate, direction, fold, seed, registry/config/model/assignment/artifact hashes where applicable. Prediction records MUST distinguish source, target adaptation, and target evaluation roles; target adaptation records MUST contain no target labels or supervision. Synthetic and blocked artifacts MUST state `real_data_run: false` and `publication_metrics_present: false`. Hash mismatch, missing artifacts, or target-label leakage MUST fail validation rather than be repaired by rewriting a manifest.

#### Scenario: Materialize a valid synthetic output

- **Given** a resolved approved candidate and completed synthetic lifecycle
- **When** output finalization runs
- **Then** all required artifacts are written atomically under the exact candidate/direction/fold/seed path, content hashes are recomputed, and the artifact index agrees with file bytes and roles

#### Scenario: Reject a partial or contaminated output

- **Given** an output with a missing required artifact, changed content, MRI data, target labels in adaptation, publication metrics, or a mismatched manifest hash
- **When** schema validation runs
- **Then** it fails closed and does not relabel or overwrite the invalid artifact as valid evidence

### Requirement: Excluded candidates MUST remain visibly blocked

The registry and equivalence manifest MUST preserve the following dispositions:

- `no_domain_adaptation`: blocked as Source-Only until no target adaptation loader is constructed, forwarded, consumed, or represented in training identity and the protected Source-Only contract is proven;
- `full`: invalid after architecture revision;
- `no_ctx_encoder`: equivalent to current no-context behavior but invalid as a patching technique;
- `identity_ctx`: helper-only;
- `no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, and `mean_pooling`: unsupported aliases absent explicit one-to-one mapping;
- `lambda_proto = 0.2`: unresolved configuration, not equivalent to the canonical primary `lambda_proto = 1.0`;
- CFS, ACS, PCS, and QIS: blocked without authoritative equations.

#### Scenario: Reject a historical Source-Only claim

- **Given** a request for `no_domain_adaptation` as `Source-Only`
- **When** no independently reviewed source-only loader/forward/output proof is present
- **Then** resolution fails with `source_only_not_proven`, retains the blocked manifest, and does not substitute the protected Source-Only method

#### Scenario: Preserve unresolved coefficient disposition

- **Given** a request that requires choosing `lambda_proto = 0.2` versus `lambda_proto = 1.0` without a separate decision
- **When** publication-facing or matrix resolution is attempted
- **Then** it fails with `unresolved_coefficient` and records both values and their provenance without selecting either as a new contract

### Requirement: Real runs and publication behavior MUST require a separate gate

This specification MUST authorize only synthetic/test implementation. No default or synthetic command MAY load or train real ADNI/OASIS data, emit publication metrics, generate scientific conclusions, or start Phase 18. A real-run request MUST fail before data loading unless a separate authorization records the exact candidate matrix, data/artifact locations, compute budget, and approved command. Native lifecycle and Phase 16 receipt boundaries remain unchanged.

#### Scenario: Run the approved synthetic smoke path

- **Given** an approved candidate, deterministic synthetic fixtures, explicit matrix, and no real-run authorization
- **When** synthetic smoke mode is requested
- **Then** it runs only in-memory/synthetic data, emits no publication result, records the synthetic boundary, and stops before Phase 18

#### Scenario: Reject an unauthorized real run

- **Given** a command or configuration that requests ADNI/OASIS data, real evaluation, publication output, or Phase 18 work without a separate authorization
- **When** preflight validation runs
- **Then** it fails with `real_run_not_authorized` (or the corresponding phase-boundary reason) before data loading and leaves prior artifacts unchanged
