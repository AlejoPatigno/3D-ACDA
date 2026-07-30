# Phase 12 Requirements — PADA-3DACB + CDAN

## Scope

Phase 12 MUST add only the `PADA-3DACB + CDAN` method. It MUST preserve the Phase 11 `PADA-3DACB + MMD` behavior and all earlier Source-Only and CORAL behavior. It MUST NOT implement Phase 13 work or any later-phase behavior.

## Scientific Requirements

### Requirement: Approved cohorts and directions only

The system MUST support only ADNI and OASIS cohorts and only the `ADNI -> OASIS` and `OASIS -> ADNI` domain-adaptation directions.

#### Scenario: Unsupported cohort or direction is rejected

- GIVEN a CDAN experiment configuration
- WHEN it names any cohort outside ADNI/OASIS or a direction outside the approved pair
- THEN configuration validation MUST fail before training starts.

### Requirement: Public model and method identity

The system MUST expose the public method label `PADA-3DACB + CDAN` and MUST keep the public model as PADA-3DACB, where PADA-3DACB is the former Lite/no-contextual-encoder architecture.

#### Scenario: Phase 12 method identity is stable

- GIVEN a CDAN run, manifest, checkpoint, prediction export, or documentation output
- WHEN method identity is recorded
- THEN it MUST identify method `cdan` and display name `PADA-3DACB + CDAN` without introducing `PADA-3DACB-Full`, `ContextualROIEncoder`, `ctx_enc`, or identity patch behavior.

### Requirement: Immutable labels and partitions

The system MUST keep class order `CN = 0`, `MCI = 1`, `AD = 2`; MUST keep source folds and target partitions immutable; MUST keep target adaptation and target evaluation disjoint; and MUST NOT use target diagnosis labels during adaptation training.

#### Scenario: Target labels do not enter adaptation

- GIVEN a target-adaptation batch for CDAN
- WHEN the trainer consumes the batch
- THEN no diagnosis label tensor from target adaptation MAY contribute to the loss, gradients, checkpoint selection, exported predictions, or domain labels.

### Requirement: Fixed-epoch source-validation selection

The system MUST use fixed epochs and MUST select the best checkpoint solely by source-validation macro-F1. Target-evaluation metrics MUST be monitoring-only.

#### Scenario: Target monitoring cannot select checkpoints

- GIVEN a CDAN run with source-validation and target-monitoring metrics
- WHEN checkpoint selection is evaluated
- THEN the selected checkpoint MUST be determined only from source-validation macro-F1 and MUST NOT use target diagnosis metrics.

### Requirement: No preprocessing, artifact, or split mutation

Experiment phases MUST NOT rerun preprocessing, artifact precomputation, concept normalizer fitting, or split generation. Concept normalizers MUST NOT be refitted per fold.

#### Scenario: CDAN run consumes existing artifacts

- GIVEN existing source folds, target partitions, concept normalizers, and precomputed artifacts
- WHEN CDAN training or validate-only execution starts
- THEN it MUST consume those artifacts as inputs and MUST NOT regenerate or mutate them.

## CDAN Tensor and Loss Contracts

### Requirement: Exact outer-product conditioning

CDAN MUST construct an exact conditional tensor from subject embedding `z ∈ R^(B,d)` and latent classifier probabilities `p ∈ R^(B,3)` from the current forward pass. For each sample, it MUST compute `H_i = z_i p_i^T` and flatten deterministically to `h ∈ R^(B, d * 3)`.

#### Scenario: Conditional tensor shape and ordering are deterministic

- GIVEN `z` with shape `(B, d)` and class probabilities with shape `(B, 3)`
- WHEN the CDAN conditional representation is built
- THEN the output shape MUST be `(B, d * 3)` and repeated construction with the same tensors MUST produce identical flattened values.

### Requirement: Gradient flow through conditioning

Neither `z` nor latent classifier probabilities MAY be detached before or during conditional tensor construction.

#### Scenario: Domain loss reaches encoder and classifier

- GIVEN a differentiable CDAN full-stage batch
- WHEN the weighted domain loss is backpropagated
- THEN gradients MUST reach the shared encoder path that produces `z`, the latent classifier path that produces probabilities, and the domain discriminator parameters.

### Requirement: Conditional dimension validation

The system SHOULD infer the conditional input dimension from the model embedding dimension and class count. It MUST validate that discriminator input dimension equals `d * 3`; with default embedding dimension `d=128`, this is 384.

#### Scenario: Dimension mismatch fails closed

- GIVEN an embedding dimension `d` and a discriminator input dimension
- WHEN the discriminator is created or used for CDAN
- THEN any input dimension other than `d * 3` MUST fail validation before silently training.

### Requirement: Constant GRL coefficient

CDAN MUST use an explicit finite non-negative constant gradient-reversal coefficient. It MUST NOT use a hidden progress schedule.

#### Scenario: GRL is finite, non-negative, and constant

- GIVEN a CDAN configuration
- WHEN the GRL coefficient is loaded
- THEN missing, negative, NaN, infinite, or scheduled coefficients MUST be rejected, and accepted coefficients MUST remain constant across warm-up/full-stage steps.

### Requirement: Discriminator logits contract

The domain discriminator MUST consume flattened conditional representations and return exactly one raw logit per sample. It MUST NOT include a final sigmoid layer.

#### Scenario: Discriminator output is compatible with BCEWithLogits

- GIVEN a conditional tensor `h ∈ R^(B, d * 3)`
- WHEN it is passed to the discriminator
- THEN the discriminator MUST return raw logits with shape `(B,)` or `(B, 1)` that are consumed by `BCEWithLogitsLoss`, with no final sigmoid activation.

### Requirement: Internal binary domain labels

The system MUST generate domain labels internally as source = 0 and target = 1.

#### Scenario: Domain labels are not user-provided

- GIVEN paired source and target batches
- WHEN CDAN domain loss is computed
- THEN the system MUST construct source-zero and target-one labels internally and MUST NOT accept external domain-label overrides.

### Requirement: Concatenated mean domain BCE

CDAN loss MUST concatenate source and target domain logits and labels and compute `BCEWithLogitsLoss(reduction="mean")`. The adaptation contribution to the training objective MUST be `cdan_weight * domain_bce`.

#### Scenario: Domain loss is scalar and finite

- GIVEN finite source and target conditional representations
- WHEN CDAN domain loss is computed
- THEN the raw domain BCE and weighted CDAN contribution MUST be finite scalar tensors and diagnostics SHOULD expose source/target domain loss and domain accuracy.

## Training Objective Requirements

### Requirement: Warm-up is source-only

Warm-up MUST remain source-only. During warm-up, the system MUST NOT consume target-adaptation batches, construct CDAN conditional features, call the discriminator, update discriminator parameters, or report nonzero CDAN loss.

#### Scenario: Warm-up has no CDAN side effects

- GIVEN a CDAN method configured with warm-up epochs
- WHEN a warm-up step runs
- THEN the step MUST optimize only the approved source objective and MUST report zero/no CDAN domain diagnostics.

### Requirement: Full-stage shared optimization

The full stage MUST use one shared PADA-3DACB model, one shared discriminator, one AdamW optimizer with explicit model and discriminator parameter groups, one backward pass, and one optimizer step per paired source-target batch.

#### Scenario: Full-stage step is a single combined update

- GIVEN a paired source-target CDAN batch
- WHEN a full-stage training step completes
- THEN source objective and weighted domain objective MUST be combined into one backward pass and one AdamW optimizer step affecting the shared model and discriminator parameter groups.

### Requirement: Source objective remains protected

CDAN MUST extend, not reinterpret, the approved source classification, concept, anatomical, consistency, and prior-method UDA contracts. Source-Only, CORAL, and MMD tests MUST remain regression-protected.

#### Scenario: Prior methods remain unchanged

- GIVEN existing Source-Only, CORAL, and MMD configurations
- WHEN Phase 12 code is present
- THEN those methods MUST keep their prior configuration validation, losses, checkpoint policy, prediction schema, and runtime behavior.

## Configuration, Hash, and Provenance Requirements

### Requirement: Explicit real-run CDAN hyperparameters

Real CDAN runs MUST require explicit finite values for CDAN weight, GRL coefficient, discriminator hidden dimensions/dropout, and discriminator optimizer settings. Missing scientific values are unresolved blockers and MUST NOT be replaced with invented real-run defaults.

#### Scenario: Missing real-run values block execution

- GIVEN a real CDAN configuration with missing adaptation weight, GRL coefficient, discriminator architecture, or discriminator optimizer settings
- WHEN it is loaded for training
- THEN validation MUST fail with an actionable configuration error.

### Requirement: Stable configuration and checkpoint identity

CDAN run directories, manifests, and checkpoints MUST include stable method/configuration identity covering the CDAN method label, conditional variant, GRL settings, discriminator configuration, discriminator optimizer group, and relevant loader generator states.

#### Scenario: CDAN identity changes when scientific settings change

- GIVEN two CDAN configurations that differ in GRL or discriminator settings
- WHEN their resolved configuration identities are computed
- THEN hashes and run identity SHOULD differ, while equivalent normalized configurations SHOULD produce stable identities.

### Requirement: Validate-only is scientific smoke only

Validate-only execution MAY compute a minimal finite CDAN objective to validate wiring, but MUST NOT claim real-run scientific results.

#### Scenario: Validate-only does not replace real training

- GIVEN validate-only mode
- WHEN CDAN validation succeeds
- THEN the result MAY prove finite tensor/loss wiring but MUST NOT be reported as a completed scientific experiment.

## Data and Monitoring Requirements

### Requirement: Prediction export policy

The system MUST export source-validation and target-monitoring predictions using the shared subject-level schema with `method=cdan` and `model=PADA-3DACB + CDAN`. It MUST NOT export target-adaptation predictions or internal domain labels.

#### Scenario: Export excludes adaptation-only data

- GIVEN a completed CDAN fold
- WHEN predictions are exported
- THEN source-validation and target-monitoring records MAY be exported, but target-adaptation prediction records and domain labels MUST be absent.

### Requirement: Monitoring remains read-only

Target evaluation and target monitoring MUST be read-only with respect to model parameters and optimizer state.

#### Scenario: Monitoring creates no gradients

- GIVEN a trained or in-training CDAN model
- WHEN target monitoring runs
- THEN model mode and gradient state MUST be restored and no optimizer update MAY occur.

## Production File Scope

### Requirement: Approved Phase 12 file scope only

Phase 12 production work MAY modify only files necessary for the CDAN method, discriminator/GRL adaptation support, CDAN configuration, train CLI integration, documentation, and tests. It MUST NOT modify preprocessing, split generation, artifact cache generation, full/contextual model files, identity patch behavior, or Phase 13 production files.

#### Scenario: Later-phase behavior is blocked

- GIVEN a Phase 12 implementation diff
- WHEN it is audited
- THEN any entropy conditioning, randomized multilinear projection, pseudo-labels, prototype alignment, baseline methods, `ContextualROIEncoder`, `ctx_enc`, identity patch behavior, preprocessing reruns, or Phase 13 files MUST be treated as out of scope.

## Unresolved Blockers

The following scientific values remain unresolved blockers for real runs and MUST be supplied explicitly before real CDAN training:

- CDAN adaptation weight for real experiments.
- Constant GRL coefficient for real experiments.
- Discriminator hidden dimensions and dropout for real experiments.
- Discriminator optimizer learning rate and weight decay for real experiments.
- Any real-run seed/fold command matrix beyond approved smoke/validate-only commands.
